from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.ai.base import AIResponse, StructureResult
from app.services.ai.fake_provider import FakeProvider

BACKEND_DIR = Path(__file__).resolve().parent.parent


def migrate(database_url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.attributes["database_url"] = database_url
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    database_url = f"sqlite:///{tmp_path / 'app.db'}"
    migrate(database_url)
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=database_url,
        data_dir=tmp_path,
        backup_dir=tmp_path / "backups",
        ai_provider="fake",
    )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def app(
    settings: Settings,
    fake_provider: FakeProvider,
) -> FastAPI:
    app = create_app(settings)
    app.state.ai_provider = fake_provider
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client


@pytest.fixture
def chapter_id(client: TestClient) -> int:
    subject_id = client.get("/api/subjects").json()[1]["id"]
    response = client.post(
        "/api/chapters", json={"subject_id": subject_id, "title": "Fonctions affines"}
    )
    chapter_id: int = response.json()["id"]
    return chapter_id


def structured(
    client: TestClient,
    chapter_id: int,
    notes: str,
    course: str,
    headers: dict[str, str] | None = None,
) -> None:
    """Prépare un chapitre avec des notes et un cours mis au propre."""
    app = client.app
    provider: FakeProvider = app.state.ai_provider  # type: ignore[attr-defined]
    provider.responses.append(AIResponse(StructureResult(clean_course=course), 100, 50))
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": notes}, headers=headers)
    response = client.post(f"/api/chapters/{chapter_id}/structure", headers=headers)
    assert response.status_code == 201, response.text
