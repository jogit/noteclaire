import sqlite3
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.services.backup_service import backup_due, prune
from tests.test_photo import photo


def test_backup_contains_database_and_images_but_no_secrets(
    client: TestClient, settings: Settings, chapter_id: int, tmp_path_factory: object
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "notes sauvegardées"})
    client.post(
        f"/api/chapters/{chapter_id}/images",
        files={"image": ("schema.jpg", photo(400, 300), "image/jpeg")},
    )
    secrets = settings.data_dir / "secrets"
    secrets.mkdir(exist_ok=True)
    (secrets / "credentials.key").write_text("secret")

    response = client.post("/api/backups")
    assert response.status_code == 201
    name = response.json()["name"]
    assert [b["name"] for b in client.get("/api/backups").json()] == [name]

    download = client.get(f"/api/backups/{name}")
    assert download.headers["content-type"] == "application/zip"
    archive_path = settings.data_dir / "downloaded.zip"
    archive_path.write_bytes(download.content)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert "app.db" in names
        assert any(n.startswith(f"images/{chapter_id}/") for n in names)
        assert not any("secrets" in n for n in names)
        archive.extract("app.db", settings.data_dir / "restored")
    restored = sqlite3.connect(settings.data_dir / "restored" / "app.db")
    assert restored.execute("SELECT raw_text FROM notes").fetchone() == ("notes sauvegardées",)
    restored.close()


def test_backup_names_cannot_escape_the_folder(client: TestClient) -> None:
    for name in ["..%2Fapp.db", "noteclaire-1.zip", "app.db"]:
        assert client.get(f"/api/backups/{name}").status_code == 404


def test_only_the_last_backups_are_kept(settings: Settings) -> None:
    settings.backup_dir.mkdir()
    for day in range(1, 11):
        (settings.backup_dir / f"noteclaire-202610{day:02d}-120000.zip").write_bytes(b"zip")
    prune(settings)
    kept = sorted(p.name for p in settings.backup_dir.iterdir())
    assert len(kept) == settings.backup_keep
    assert kept[0] == "noteclaire-20261004-120000.zip"


def test_backup_is_due_once_a_day(client: TestClient, settings: Settings) -> None:
    assert backup_due(settings)
    client.post("/api/backups")
    assert not backup_due(settings)
    assert backup_due(settings, datetime.now(UTC) + timedelta(hours=25))


def add_image(client: TestClient, chapter_id: int) -> None:
    client.post(
        f"/api/chapters/{chapter_id}/images",
        files={"image": ("schema.jpg", photo(400, 300), "image/jpeg")},
    )


def test_restore_brings_back_notes_and_images_and_keeps_a_safety_copy(
    client: TestClient, settings: Settings, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "version sauvegardée"})
    add_image(client, chapter_id)
    name = client.post("/api/backups").json()["name"]

    # Après la sauvegarde : notes modifiées, chapitre ajouté, image supprimée à la main.
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "version perdue"})
    subject_id = client.get("/api/subjects").json()[0]["id"]
    client.post("/api/chapters", json={"subject_id": subject_id, "title": "Chapitre en trop"})
    for image in (settings.data_dir / "images").rglob("*.*"):
        image.unlink()

    assert client.post(f"/api/backups/{name}/restore").status_code == 204

    notes = client.get(f"/api/chapters/{chapter_id}/notes").json()
    assert notes["raw_text"] == "version sauvegardée"
    assert [c["title"] for c in client.get("/api/chapters").json()] == ["Fonctions affines"]
    assert any((settings.data_dir / "images").rglob("*.*"))
    # La copie de sécurité contient l'état d'avant la restauration.
    assert len(client.get("/api/backups").json()) == 2
    client.post(f"/api/backups/{client.get('/api/backups').json()[0]['name']}/restore")
    assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == "version perdue"


def test_restore_from_uploaded_file(client: TestClient, chapter_id: int) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "à garder"})
    name = client.post("/api/backups").json()["name"]
    content = client.get(f"/api/backups/{name}").content
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "à oublier"})

    response = client.post(
        "/api/backups/restore", files={"file": ("sauvegarde.zip", content, "application/zip")}
    )
    assert response.status_code == 204
    assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == "à garder"


def test_restore_refuses_bad_archives_without_touching_data(
    client: TestClient, settings: Settings, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "intactes"})

    def restore(content: bytes) -> str:
        files = {"file": ("x.zip", content, "application/zip")}
        return str(client.post("/api/backups/restore", files=files).json()["error"]["code"])

    assert restore(b"pas un zip") == "backup_invalid"

    evil = settings.data_dir / "evil.zip"
    with zipfile.ZipFile(evil, "w") as archive:
        archive.writestr("app.db", b"x")
        archive.writestr("images/../../evil.txt", b"x")
    assert restore(evil.read_bytes()) == "backup_invalid"

    broken = settings.data_dir / "broken.zip"
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("app.db", b"ceci n'est pas une base SQLite")
    assert restore(broken.read_bytes()) == "backup_invalid"

    other_version = settings.data_dir / "other.sqlite"
    database = sqlite3.connect(other_version)
    database.execute("CREATE TABLE alembic_version (version_num TEXT)")
    database.execute("INSERT INTO alembic_version VALUES ('0000')")
    database.commit()
    database.close()
    other = settings.data_dir / "other.zip"
    with zipfile.ZipFile(other, "w") as archive:
        archive.write(other_version, "app.db")
    assert restore(other.read_bytes()) == "backup_incompatible"

    assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == "intactes"
    assert client.get("/api/backups").json() == []  # aucune copie de sécurité inutile


def test_restore_refuses_oversized_archives(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.services.backup_service.MAX_RESTORED_BYTES", 10)
    big = settings.data_dir / "big.zip"
    with zipfile.ZipFile(big, "w") as archive:
        archive.writestr("app.db", b"x" * 100)
    files = {"file": ("x.zip", big.read_bytes(), "application/zip")}
    response = client.post("/api/backups/restore", files=files)
    assert (response.status_code, response.json()["error"]["code"]) == (413, "backup_too_large")
