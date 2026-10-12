import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.main import create_app
from app.models import AIRun
from app.services.ai.base import (
    AIProviderError,
    StructureRequest,
    StructureResponse,
    StructureResult,
)
from app.services.ai.fake_provider import FakeProvider

NOTES = "fonction affine f(x)=ax+b\na c'est le coef directeur"


def ok(content: str = "# Fonctions affines\n\nContenu") -> StructureResponse:
    return StructureResponse(StructureResult(clean_course=content), 120, 80)


def ai_runs(app: FastAPI) -> list[AIRun]:
    with app.state.db.session_factory() as session:
        return list(session.scalars(select(AIRun).order_by(AIRun.id)))


@pytest.fixture
def with_notes(client: TestClient, chapter_id: int) -> int:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": NOTES})
    return chapter_id


def test_structure_creates_course_and_keeps_notes(
    client: TestClient, app: FastAPI, fake_provider: FakeProvider, with_notes: int
) -> None:
    fake_provider.responses.append(ok())

    response = client.post(f"/api/chapters/{with_notes}/structure")

    assert response.status_code == 201
    course = response.json()
    assert course["content_markdown"] == "# Fonctions affines\n\nContenu"
    assert course["version"] == 1
    assert course["origin"] == "ai_structure"
    assert course["notes_changed"] is False
    assert client.get(f"/api/chapters/{with_notes}/notes").json()["raw_text"] == NOTES
    assert client.get(f"/api/chapters/{with_notes}/course").json() == course

    request = fake_provider.requests[0]
    assert isinstance(request, StructureRequest)
    assert (request.subject, request.chapter, request.raw_notes) == (
        "Mathématiques",
        "Fonctions affines",
        NOTES,
    )
    [run] = ai_runs(app)
    assert (run.status, run.operation, run.provider) == ("success", "structure", "fake")
    assert (run.input_tokens, run.output_tokens) == (120, 80)
    assert len(run.input_hash) == 64


def test_each_structure_creates_a_new_version(client: TestClient, with_notes: int) -> None:
    client.post(f"/api/chapters/{with_notes}/structure")
    second = client.post(f"/api/chapters/{with_notes}/structure").json()
    assert second["version"] == 2


def test_notes_changed_after_structure(client: TestClient, with_notes: int) -> None:
    client.post(f"/api/chapters/{with_notes}/structure")
    client.put(f"/api/chapters/{with_notes}/notes", json={"raw_text": NOTES + "\nb ordonnée"})
    assert client.get(f"/api/chapters/{with_notes}/course").json()["notes_changed"] is True


def test_course_absent_before_structure(client: TestClient, chapter_id: int) -> None:
    assert client.get(f"/api/chapters/{chapter_id}/course").status_code == 404


def test_empty_notes_are_refused(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "   \n"})
    response = client.post(f"/api/chapters/{chapter_id}/structure")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "empty_notes"
    assert fake_provider.requests == []


def test_invalid_response_is_retried_once(
    client: TestClient, app: FastAPI, fake_provider: FakeProvider, with_notes: int
) -> None:
    fake_provider.responses.extend([AIProviderError("ai_invalid_response"), ok()])

    response = client.post(f"/api/chapters/{with_notes}/structure")

    assert response.status_code == 201
    assert [(r.status, r.error_code) for r in ai_runs(app)] == [
        ("error", "ai_invalid_response"),
        ("success", None),
    ]


def test_two_invalid_responses_give_an_explicit_error(
    client: TestClient, fake_provider: FakeProvider, with_notes: int
) -> None:
    fake_provider.responses.extend([AIProviderError("ai_invalid_response")] * 2)

    response = client.post(f"/api/chapters/{with_notes}/structure")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ai_invalid_response"
    assert client.get(f"/api/chapters/{with_notes}/course").status_code == 404


def test_timeout_is_not_retried(
    client: TestClient, app: FastAPI, fake_provider: FakeProvider, with_notes: int
) -> None:
    fake_provider.responses.extend([AIProviderError("ai_timeout"), ok()])

    response = client.post(f"/api/chapters/{with_notes}/structure")

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "ai_timeout"
    assert len(ai_runs(app)) == 1


def test_course_content_is_not_logged(
    client: TestClient, with_notes: int, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    client.post(f"/api/chapters/{with_notes}/structure")
    assert "coef directeur" not in caplog.text


def test_app_works_without_api_key(settings: Settings) -> None:
    no_key = settings.model_copy(update={"ai_provider": "openai", "openai_api_key": ""})
    with TestClient(create_app(no_key)) as client:
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Poésie"}
        ).json()["id"]
        client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "Baudelaire"})

        response = client.post(f"/api/chapters/{chapter_id}/structure")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ai_not_configured"
