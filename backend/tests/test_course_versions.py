from fastapi.testclient import TestClient

from tests.conftest import structured


def test_manual_edit_creates_a_version(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "mes notes", "# Cours\n\nmes notes\n")

    response = client.put(
        f"/api/chapters/{chapter_id}/course", json={"content_markdown": "# Cours\n\nretouché\n"}
    )

    course = response.json()
    assert (course["version"], course["origin"]) == (2, "user_edit")
    assert course["has_manual_changes"] is True
    assert course["notes_changed"] is False
    assert client.get(f"/api/chapters/{chapter_id}/notes").json()["raw_text"] == "mes notes"


def test_identical_edit_does_not_create_a_version(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", "# Cours\n")
    course = client.put(
        f"/api/chapters/{chapter_id}/course", json={"content_markdown": "# Cours\n"}
    ).json()
    assert course["version"] == 1


def test_empty_edit_is_refused(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", "# Cours\n")
    response = client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "  "})
    assert response.json()["error"]["code"] == "empty_course"


def test_edit_requires_a_course(client: TestClient, chapter_id: int) -> None:
    response = client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "x"})
    assert response.status_code == 404


def test_restructure_resets_manual_changes_flag(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", "# Cours\n")
    client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "# Retouché\n"})
    structured(client, chapter_id, "notes", "# Cours v3\n")
    course = client.get(f"/api/chapters/{chapter_id}/course").json()
    assert (course["version"], course["has_manual_changes"]) == (3, False)


def test_versions_history(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", "# Cours\n")
    client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "# Retouché\n"})

    versions = client.get(f"/api/chapters/{chapter_id}/course/versions").json()

    assert [(v["version"], v["origin"]) for v in versions] == [
        (2, "user_edit"),
        (1, "ai_structure"),
    ]
    assert "content_markdown" not in versions[0]
    first = client.get(f"/api/chapters/{chapter_id}/course/versions/1").json()
    assert first["content_markdown"] == "# Cours\n"
    assert client.get(f"/api/chapters/{chapter_id}/course/versions/9").status_code == 404


def test_notes_source_is_saved(client: TestClient, chapter_id: int) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "dicté", "source": "photo"})
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "dicté et tapé"})
    notes = client.get(f"/api/chapters/{chapter_id}/notes").json()
    assert (notes["raw_text"], notes["source"]) == ("dicté et tapé", "photo")
    bad = client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "x", "source": "scan"})
    assert bad.status_code == 422


def test_course_title_is_its_first_level_one_heading(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", "Intro\n\n## Partie\n\n# Les vecteurs #\n\n# Autre\n")
    assert client.get(f"/api/chapters/{chapter_id}/course").json()["title"] == "Les vecteurs"
    client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "Pas de titre"})
    assert client.get(f"/api/chapters/{chapter_id}/course").json()["title"] == ""
