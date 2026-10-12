from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.models import Chapter, NoteVersion
from app.models.entities import utcnow
from app.services.trash_service import purge_expired


def test_deleted_chapter_goes_to_trash_and_can_be_restored(
    client: TestClient, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "vecteur colinéaire"})
    subject_id = client.get(f"/api/chapters/{chapter_id}").json()["subject_id"]

    assert client.delete(f"/api/chapters/{chapter_id}").status_code == 204
    assert client.get(f"/api/chapters/{chapter_id}").status_code == 404
    assert client.get("/api/chapters").json() == []
    assert client.get("/api/search", params={"q": "colinéaire"}).json() == []
    counts = {s["id"]: s["chapter_count"] for s in client.get("/api/subjects").json()}
    assert counts[subject_id] == 0
    trash = client.get("/api/trash").json()
    assert [item["id"] for item in trash] == [chapter_id]
    assert trash[0]["title"] == "Fonctions affines"

    restored = client.post(f"/api/trash/{chapter_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["id"] == chapter_id
    assert client.get("/api/trash").json() == []
    notes = client.get(f"/api/chapters/{chapter_id}/notes").json()
    assert notes["raw_text"] == "vecteur colinéaire"
    assert len(client.get("/api/search", params={"q": "colinéaire"}).json()) == 1


def test_purge_deletes_for_good(client: TestClient, chapter_id: int) -> None:
    assert client.delete(f"/api/trash/{chapter_id}").status_code == 404  # pas à la corbeille
    client.delete(f"/api/chapters/{chapter_id}")
    assert client.delete(f"/api/trash/{chapter_id}").status_code == 204
    assert client.get("/api/trash").json() == []
    assert client.post(f"/api/trash/{chapter_id}/restore").status_code == 404


def test_trash_is_emptied_after_30_days(
    client: TestClient, app: FastAPI, settings: Settings, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "un deux trois"})
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "un", "checkpoint": "photo"})
    client.delete(f"/api/chapters/{chapter_id}")
    with app.state.db.session_factory() as db:
        assert purge_expired(db, settings) == 0
        db.get(Chapter, chapter_id).deleted_at = utcnow() - timedelta(days=31)
        db.commit()
        assert purge_expired(db, settings) == 1
        assert db.get(Chapter, chapter_id) is None
        assert db.scalars(select(NoteVersion)).all() == []
