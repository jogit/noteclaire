import stat
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import ai_config


def test_fake_provider_needs_no_setup(client: TestClient) -> None:
    status = client.get("/api/setup/status").json()
    assert status["needs_setup"] is False
    assert status["ai_provider"] == "fake"


def test_openai_without_key_needs_setup_then_key_is_saved_privately(
    settings: Settings, client: TestClient
) -> None:
    settings.ai_provider = "openai"
    assert client.get("/api/setup/status").json()["needs_setup"] is True

    response = client.put(
        "/api/setup/ai", json={"ai_provider": "openai", "openai_api_key": "sk-secret-123"}
    )
    status = response.json()
    assert (status["needs_setup"], status["has_openai_key"]) == (False, True)
    assert "sk-secret-123" not in response.text

    path = settings.data_dir / "secrets" / "ai.enc"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert b"sk-secret-123" not in path.read_bytes()  # chiffré
    assert settings.openai_api_key == "sk-secret-123"

    # Une clé laissée vide garde la précédente.
    client.put("/api/setup/ai", json={"ai_provider": "openai"})
    assert settings.openai_api_key == "sk-secret-123"


def test_saved_choice_overrides_env_at_startup(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        client.put(
            "/api/setup/ai",
            json={"ai_provider": "local", "local_ai_base_url": "http://ia:1234/v1"},
        )
    settings.ai_provider = "openai"
    settings.local_ai_base_url = "http://autre"
    with TestClient(create_app(settings)):
        assert str(settings.ai_provider) == "local"
        assert settings.local_ai_base_url == "http://ia:1234/v1"


class FakeModels:
    def __init__(self, fail: bool) -> None:
        self.fail = fail

    async def list(self) -> list[Any]:
        if self.fail:
            raise RuntimeError("401 sk-secret-123 invalid")
        return []


@pytest.mark.parametrize(("fail", "ok"), [(False, True), (True, False)])
def test_connection_test_hides_errors(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, fail: bool, ok: bool
) -> None:
    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.models = FakeModels(fail)

    monkeypatch.setattr(ai_config, "AsyncOpenAI", FakeClient)
    client.put("/api/setup/ai", json={"ai_provider": "openai", "openai_api_key": "sk-secret-123"})
    result = client.post("/api/setup/ai/test")
    assert result.json()["ok"] is ok
    assert "sk-secret-123" not in result.text


def test_unreadable_saved_choice_is_ignored(settings: Settings) -> None:
    secrets = settings.data_dir / "secrets"
    secrets.mkdir()
    (secrets / "ai.enc").write_bytes(b"abime")
    with TestClient(create_app(settings)):
        pass  # le démarrage ne plante pas
