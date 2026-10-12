from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.subjects import DEFAULTS_BY_LEVEL, SUBJECTS
from tests.conftest import structured


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_subjects_are_seeded_in_order(client: TestClient) -> None:
    subjects = client.get("/api/subjects").json()
    assert [s["slug"] for s in subjects] == [
        slug for slug, _ in SUBJECTS if slug in DEFAULTS_BY_LEVEL["seconde"]
    ]
    assert subjects[1]["name"] == "Mathématiques"


def test_seeding_is_idempotent(settings: Settings) -> None:
    for _ in range(2):
        with TestClient(create_app(settings)) as client:
            assert len(client.get("/api/subjects").json()) == len(DEFAULTS_BY_LEVEL["seconde"])


def test_create_and_list_chapters(client: TestClient, chapter_id: int) -> None:
    chapter = client.get(f"/api/chapters/{chapter_id}").json()
    assert chapter["title"] == "Fonctions affines"
    assert chapter["subject"]["slug"] == "mathematiques"

    subject_id = chapter["subject_id"]
    assert [c["id"] for c in client.get(f"/api/chapters?subject_id={subject_id}").json()] == [
        chapter_id
    ]
    other_subject = client.get("/api/subjects").json()[0]["id"]
    assert client.get(f"/api/chapters?subject_id={other_subject}").json() == []


def test_create_chapter_validation(client: TestClient) -> None:
    response = client.post("/api/chapters", json={"subject_id": 9999, "title": "X"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unknown_subject"
    assert client.post("/api/chapters", json={"subject_id": 1, "title": ""}).status_code == 422


def test_update_and_delete_chapter(client: TestClient, chapter_id: int) -> None:
    response = client.patch(f"/api/chapters/{chapter_id}", json={"title": "  Vecteurs  "})
    assert response.json()["title"] == "Vecteurs"

    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "notes"})
    client.post(f"/api/chapters/{chapter_id}/structure")
    assert client.delete(f"/api/chapters/{chapter_id}").status_code == 204
    assert client.get(f"/api/chapters/{chapter_id}").status_code == 404
    assert client.get(f"/api/chapters/{chapter_id}/course").status_code == 404


def test_unknown_chapter(client: TestClient) -> None:
    response = client.get("/api/chapters/404")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_notes_are_created_empty_and_saved(client: TestClient, chapter_id: int) -> None:
    assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == ""

    response = client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "f(x) = ax + b"})
    assert response.status_code == 200
    notes = client.get(f"/api/chapters/{chapter_id}/notes").json()
    assert notes["raw_text"] == "f(x) = ax + b"
    assert notes["source"] == "keyboard"
    assert notes["updated_at"].endswith("Z") or "+00:00" in notes["updated_at"]


def test_data_survives_restart(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        subject_id = client.get("/api/subjects").json()[0]["id"]
        chapter_id = client.post(
            "/api/chapters", json={"subject_id": subject_id, "title": "Le roman"}
        ).json()["id"]
        client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "Balzac"})

    with TestClient(create_app(settings)) as client:
        assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == "Balzac"


def test_chapter_progress_and_subject_counts(client: TestClient, chapter_id: int) -> None:
    progress = client.get(f"/api/chapters/{chapter_id}").json()["progress"]
    assert progress == {
        "notes_words": 0,
        "course_version": None,
        "notes_changed": False,
        "pending_suggestions": 0,
        "has_revision_sheet": False,
        "has_quiz": False,
    }

    structured(client, chapter_id, "trois mots ici", "# Cours\n")
    client.post(f"/api/chapters/{chapter_id}/revision-sheet")
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "notes modifiées"})

    [listed] = client.get("/api/chapters").json()
    assert listed["progress"] == {
        "notes_words": 2,
        "course_version": 1,
        "notes_changed": True,
        "pending_suggestions": 0,
        "has_revision_sheet": True,
        "has_quiz": False,
    }
    counts = {s["slug"]: s["chapter_count"] for s in client.get("/api/subjects").json()}
    assert counts["mathematiques"] == 1
    assert counts["francais"] == 0


def test_manage_subjects(client: TestClient, chapter_id: int) -> None:
    created = client.post("/api/subjects", json={"name": "Latin"})
    assert created.status_code == 201
    latin = created.json()
    assert latin["slug"] == "latin"
    assert client.post("/api/subjects", json={"name": " latin "}).json()["error"]["code"] == (
        "subject_exists"
    )
    assert client.get("/api/subjects").json()[-1]["name"] == "Latin"

    renamed = client.patch(f"/api/subjects/{latin['id']}", json={"name": "Latin LCA"}).json()
    assert (renamed["name"], renamed["slug"]) == ("Latin LCA", "latin")

    [student] = client.get("/api/students").json()
    kept = [i for i in student["subject_ids"] if i != latin["id"]]
    client.put(f"/api/students/{student['id']}/subjects", json={"subject_ids": kept})
    assert "Latin LCA" not in [s["name"] for s in client.get("/api/subjects").json()]
    shown = client.get("/api/subjects", params={"include_all": True}).json()
    assert [s["enabled"] for s in shown if s["name"] == "Latin LCA"] == [False]

    assert client.delete(f"/api/subjects/{latin['id']}").status_code == 204
    maths = client.get(f"/api/chapters/{chapter_id}").json()["subject_id"]
    assert client.delete(f"/api/subjects/{maths}").json()["error"]["code"] == "subject_not_empty"


def test_deleted_default_subject_is_not_recreated(settings: Settings) -> None:
    with TestClient(create_app(settings)) as client:
        sport = client.get("/api/subjects").json()[0]
        assert client.delete(f"/api/subjects/{sport['id']}").status_code == 204
    with TestClient(create_app(settings)) as client:
        assert len(client.get("/api/subjects").json()) == len(DEFAULTS_BY_LEVEL["seconde"]) - 1


def test_subjects_are_enabled_per_student(client: TestClient) -> None:
    lea = client.post("/api/students", json={"name": "Léa", "level": "terminale"}).json()
    headers = {"X-Student-Id": str(lea["id"])}

    slugs = {s["slug"] for s in client.get("/api/subjects", headers=headers).json()}
    assert slugs == DEFAULTS_BY_LEVEL["terminale"]
    assert "snt" not in slugs
    assert "snt" in {s["slug"] for s in client.get("/api/subjects").json()}

    # Une matière créée par Léa est pour elle seule, jusqu'à ce qu'on l'active ailleurs.
    latin = client.post("/api/subjects", json={"name": "Latin"}, headers=headers).json()
    assert "Latin" not in [s["name"] for s in client.get("/api/subjects").json()]
    [first, _] = client.get("/api/students").json()
    client.put(
        f"/api/students/{first['id']}/subjects",
        json={"subject_ids": [*first["subject_ids"], latin["id"]]},
    )
    assert "Latin" in [s["name"] for s in client.get("/api/subjects").json()]
    unknown = client.put(f"/api/students/{lea['id']}/subjects", json={"subject_ids": [9999]})
    assert unknown.json()["error"]["code"] == "unknown_subject"

    # Sans chapitre, changer de classe remet les matières habituelles de la nouvelle classe.
    client.patch(f"/api/students/{lea['id']}", json={"level": "premiere"})
    slugs = {s["slug"] for s in client.get("/api/subjects", headers=headers).json()}
    assert slugs == DEFAULTS_BY_LEVEL["premiere"]


def test_subjects_tell_which_classes_they_are_usual_for(client: TestClient) -> None:
    subjects = {
        s["slug"]: s for s in client.get("/api/subjects", params={"include_all": True}).json()
    }
    assert "seconde" in subjects["snt"]["usual_for"]
    assert subjects["philosophie"]["usual_for"] == ["terminale", "terminale-techno"]
    assert subjects["stmg"]["usual_for"] == []  # une série se coche à la main


def test_version(client: TestClient) -> None:
    assert client.get("/api/version").json() == {"version": "dev"}
