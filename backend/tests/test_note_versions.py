from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import update

from app.models import NoteVersion
from app.models.entities import utcnow
from app.services.chapter_service import MAX_NOTE_VERSIONS
from tests.conftest import structured

LONG_NOTES = " ".join(f"mot{i}" for i in range(40))


def put(client: TestClient, chapter_id: int, text: str, **extra: str) -> None:
    response = client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": text, **extra})
    assert response.status_code == 200


def versions(client: TestClient, chapter_id: int) -> list[dict[str, object]]:
    response = client.get(f"/api/chapters/{chapter_id}/notes/versions")
    assert response.status_code == 200
    result: list[dict[str, object]] = response.json()
    return result


def age_versions(app: FastAPI, minutes: int) -> None:
    with app.state.db.session_factory() as db:
        db.execute(update(NoteVersion).values(created_at=utcnow() - timedelta(minutes=minutes)))
        db.commit()


def test_photo_checkpoint_keeps_the_imported_text(client: TestClient, chapter_id: int) -> None:
    put(client, chapter_id, "texte de la photo", source="photo", checkpoint="photo")

    [version] = versions(client, chapter_id)
    assert version["reason"] == "photo"
    assert version["words"] == 4
    assert version["preview"] == "texte de la photo"


def test_automatic_version_at_most_every_15_minutes(
    client: TestClient, app: FastAPI, chapter_id: int
) -> None:
    put(client, chapter_id, "premier jet")
    put(client, chapter_id, "premier jet corrigé")  # état précédent gardé : aucune version
    put(client, chapter_id, "premier jet corrigé encore")
    assert [v["reason"] for v in versions(client, chapter_id)] == ["auto"]

    age_versions(app, 20)
    put(client, chapter_id, "deuxième séance")
    texts = [
        client.get(f"/api/chapters/{chapter_id}/notes/versions/{v['id']}").json()["raw_text"]
        for v in versions(client, chapter_id)
    ]
    assert texts == ["premier jet corrigé encore", "premier jet"]


def test_big_deletion_is_always_kept(client: TestClient, chapter_id: int) -> None:
    put(client, chapter_id, LONG_NOTES, checkpoint="photo")
    put(client, chapter_id, "presque tout effacé")
    put(client, chapter_id, "presque tout effacé, puis complété")

    reasons = [v["reason"] for v in versions(client, chapter_id)]
    assert reasons == ["photo"]  # le texte effacé est déjà la dernière version

    put(client, chapter_id, LONG_NOTES + " suite")
    put(client, chapter_id, "vide")
    assert versions(client, chapter_id)[0]["reason"] == "big_deletion"


def test_restore_keeps_current_notes(client: TestClient, chapter_id: int) -> None:
    put(client, chapter_id, "version A", checkpoint="photo")
    put(client, chapter_id, "version B")
    [photo] = versions(client, chapter_id)

    response = client.post(f"/api/chapters/{chapter_id}/notes/versions/{photo['id']}/restore")
    assert response.status_code == 200
    assert response.json()["raw_text"] == "version A"
    latest = versions(client, chapter_id)[0]
    assert latest["reason"] == "before_restore"
    assert latest["preview"] == "version B"


def test_structure_keeps_the_notes_used(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes du jour", "# Cours")
    assert versions(client, chapter_id)[0]["reason"] == "structure"


def test_only_the_last_versions_are_kept(client: TestClient, app: FastAPI, chapter_id: int) -> None:
    for i in range(MAX_NOTE_VERSIONS + 5):
        put(client, chapter_id, f"état {i}", checkpoint="photo")
    listed = versions(client, chapter_id)
    assert len(listed) == MAX_NOTE_VERSIONS
    assert listed[0]["preview"] == f"état {MAX_NOTE_VERSIONS + 4}"


def test_versions_of_another_chapter_are_not_found(client: TestClient, chapter_id: int) -> None:
    put(client, chapter_id, "texte", checkpoint="photo")
    [version] = versions(client, chapter_id)
    other = client.post("/api/chapters", json={"subject_id": 1, "title": "Autre"}).json()["id"]
    assert client.get(f"/api/chapters/{other}/notes/versions/{version['id']}").status_code == 404
    assert client.get("/api/chapters/999/notes/versions").status_code == 404
