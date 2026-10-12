from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.models import AIRun
from app.services.ai.fake_provider import FakeProvider
from tests.conftest import structured


def add_run(app: FastAPI, **values: object) -> None:
    defaults: dict[str, object] = {
        "operation": "structure",
        "provider": "chatgpt",
        "model": "gpt-5.5",
        "prompt_version": "v",
        "input_hash": "h",
        "status": "success",
        "duration_ms": 1000,
    }
    with app.state.db.session_factory() as session:
        session.add(AIRun(**(defaults | values)))
        session.commit()


def test_usage_details(app: FastAPI, client: TestClient, chapter_id: int) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    add_run(app, chapter_id=chapter_id, input_tokens=100, output_tokens=50)
    add_run(app, chapter_id=chapter_id, input_tokens=200, output_tokens=80)
    add_run(app, status="error", error_code="ai_timeout")
    add_run(app, operation="quiz", chapter_id=chapter_id, input_tokens=10, output_tokens=5)
    add_run(
        app,
        chapter_id=chapter_id,
        input_tokens=999,
        output_tokens=999,
        created_at=now - timedelta(days=40),
    )

    details = client.get("/api/usage/details").json()

    week = {row["operation"]: row for row in details["last_7_days"]}
    assert week["structure"] == {
        "operation": "structure",
        "calls": 3,
        "errors": 1,
        "input_tokens": 300,
        "output_tokens": 130,
        "cost_eur": 0.0,
    }
    assert week["quiz"]["calls"] == 1
    assert details["recent"][0]["operation"] == "quiz"  # le plus récent en premier
    assert details["recent"][-1]["input_tokens"] == 999
    # seuls les appels sur les chapitres de l'élève sont listés
    assert {r["chapter_title"] for r in details["recent"]} == {"Fonctions affines"}
    assert details["chatgpt_usage_url"] == "https://chatgpt.com/settings/usage"


def test_free_providers_have_no_cost(settings: Settings) -> None:
    priced = settings.model_copy(
        update={"ai_input_price_eur_per_mtok": 1.0, "ai_output_price_eur_per_mtok": 1.0}
    )
    app = create_app(priced)
    provider = FakeProvider()
    provider.paid = False
    app.state.ai_provider = provider
    with TestClient(app) as client:
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Poésie"}
        ).json()["id"]
        structured(client, chapter_id, "notes", "# Cours\n")
        assert client.get("/api/usage").json()["month_cost_eur"] == 0
        [row] = client.get("/api/usage/details").json()["this_month"]
        assert (row["input_tokens"], row["cost_eur"]) == (100, 0.0)


def test_typical_durations_use_recent_successful_runs(client: TestClient, app: FastAPI) -> None:
    assert client.get("/api/usage/durations").json()["structure"] == 20.0  # valeur par défaut

    with app.state.db.session_factory() as db:
        for duration, status in [(8000, "success"), (12000, "success"), (90000, "error")]:
            db.add(
                AIRun(
                    operation="structure",
                    provider="fake",
                    model="m",
                    prompt_version="v",
                    input_hash="h",
                    status=status,
                    duration_ms=duration,
                )
            )
        db.commit()

    durations = client.get("/api/usage/durations").json()
    assert durations["structure"] == 10.0
    assert durations["analyze"] == 30.0
