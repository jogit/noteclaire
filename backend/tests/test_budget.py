from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.ai.fake_provider import FakeProvider
from app.services.ai_runs import estimate_cost
from tests.conftest import structured


def priced(settings: Settings, budget: float) -> Settings:
    return settings.model_copy(
        update={
            "ai_monthly_budget_eur": budget,
            "ai_input_price_eur_per_mtok": 1.0,
            "ai_output_price_eur_per_mtok": 10.0,
        }
    )


def test_estimate_cost(settings: Settings) -> None:
    assert estimate_cost(settings, 100, 50) is None
    assert estimate_cost(priced(settings, 5), 1_000_000, 100_000) == 2.0
    assert estimate_cost(priced(settings, 5), None, 10) is None


def test_usage_without_prices(client: TestClient) -> None:
    assert client.get("/api/usage").json() == {
        "month_cost_eur": 0,
        "budget_eur": 5,
        "cost_tracking": False,
    }


def test_budget_blocks_ai_but_not_the_rest(settings: Settings) -> None:
    # 100 tokens en entrée + 50 en sortie = 0,0006 € avec ces prix ; budget atteint au 1er appel.
    app = create_app(priced(settings, 0.0005))
    app.state.ai_provider = FakeProvider()
    with TestClient(app) as client:
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Poésie"}
        ).json()["id"]
        structured(client, chapter_id, "notes", "# Cours\n")

        usage = client.get("/api/usage").json()
        assert usage["month_cost_eur"] == 0.0006
        assert usage["cost_tracking"] is True

        response = client.post(f"/api/chapters/{chapter_id}/structure")
        assert response.status_code == 429
        assert response.json()["error"]["code"] == "ai_budget_exceeded"
        assert client.post(f"/api/chapters/{chapter_id}/analyze").status_code == 429
        assert (
            client.put(
                f"/api/chapters/{chapter_id}/notes", json={"raw_text": "toujours possible"}
            ).status_code
            == 200
        )


def test_zero_budget_means_no_limit(settings: Settings) -> None:
    app = create_app(priced(settings, 0))
    app.state.ai_provider = FakeProvider()
    with TestClient(app) as client:
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Poésie"}
        ).json()["id"]
        for _ in range(3):
            structured(client, chapter_id, "notes", "# Cours\n")
