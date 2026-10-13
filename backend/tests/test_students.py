from fastapi.testclient import TestClient

from app.services.ai.base import AnalyzeRequest, ExplainRequest, StructureRequest
from app.services.ai.fake_provider import FakeProvider
from tests.conftest import structured


def other_student(client: TestClient, level: str = "premiere") -> dict[str, str]:
    created = client.post("/api/students", json={"name": "Léa", "level": level}).json()
    return {"X-Student-Id": str(created["id"])}


def test_a_default_student_is_created_at_startup(client: TestClient) -> None:
    [student] = client.get("/api/students").json()
    assert (student["name"], student["level"]) == ("Élève", "seconde")
    assert [level["id"] for level in client.get("/api/levels").json()] == [
        "seconde",
        "premiere",
        "terminale",
        "premiere-techno",
        "terminale-techno",
    ]


def test_create_update_and_validate_level(client: TestClient) -> None:
    created = client.post("/api/students", json={"name": "  Léa ", "level": "terminale"})
    assert created.status_code == 201
    assert created.json()["name"] == "Léa"

    updated = client.patch(f"/api/students/{created.json()['id']}", json={"level": "premiere"})
    assert updated.json()["level"] == "premiere"

    bad = client.post("/api/students", json={"name": "X", "level": "cm2"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_level"
    assert client.patch("/api/students/999", json={"name": "Y"}).status_code == 404


def test_chapters_search_counts_and_trash_are_separate(client: TestClient, chapter_id: int) -> None:
    lea = other_student(client)
    subject_id = client.get("/api/subjects").json()[1]["id"]
    client.post("/api/chapters", json={"subject_id": subject_id, "title": "Suites"}, headers=lea)

    assert [c["title"] for c in client.get("/api/chapters").json()] == ["Fonctions affines"]
    assert [c["title"] for c in client.get("/api/chapters", headers=lea).json()] == ["Suites"]

    assert client.get("/api/search", params={"q": "suites"}).json() == []
    assert len(client.get("/api/search", params={"q": "suites"}, headers=lea).json()) == 1

    assert client.get("/api/subjects").json()[1]["chapter_count"] == 1
    assert client.get("/api/subjects", headers=lea).json()[1]["chapter_count"] == 1
    assert client.get("/api/subjects").json()[0]["chapter_count"] == 0

    client.delete(f"/api/chapters/{chapter_id}")
    assert len(client.get("/api/trash").json()) == 1
    assert client.get("/api/trash", headers=lea).json() == []


def test_unknown_student_header_falls_back_to_the_first_student(
    client: TestClient, chapter_id: int
) -> None:
    other_student(client)
    response = client.get("/api/chapters", headers={"X-Student-Id": "999"})
    assert [c["title"] for c in response.json()] == ["Fonctions affines"]


def test_delete_student_rules(client: TestClient, chapter_id: int) -> None:
    [first] = client.get("/api/students").json()
    assert client.delete(f"/api/students/{first['id']}").json()["error"]["code"] == "last_student"

    lea = other_student(client)
    assert client.delete(f"/api/students/{first['id']}").json()["error"]["code"] == (
        "student_has_chapters"
    )
    assert client.delete(f"/api/students/{lea['X-Student-Id']}").status_code == 204
    assert len(client.get("/api/students").json()) == 1


def test_student_level_is_sent_to_the_ai(client: TestClient, fake_provider: FakeProvider) -> None:
    lea = other_student(client, "terminale")
    subject_id = client.get("/api/subjects").json()[1]["id"]
    chapter = client.post(
        "/api/chapters", json={"subject_id": subject_id, "title": "Limites"}, headers=lea
    ).json()
    structured(client, chapter["id"], "notes", "# Limites\n\nTexte.", headers=lea)
    assert isinstance(fake_provider.requests[-1], StructureRequest)
    assert fake_provider.requests[-1].level == "terminale générale"

    client.post(f"/api/chapters/{chapter['id']}/analyze", headers=lea)
    request = fake_provider.requests[-1]
    assert isinstance(request, AnalyzeRequest)
    assert request.level == "terminale générale"


def test_adaptations_are_sent_to_explanations_only_when_filled(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    [student] = client.get("/api/students").json()
    assert (student["adaptation_codes"], student["adaptation_notes"]) == ([], "")
    structured(client, chapter_id, "notes", "# Cours\n\nTexte.")

    def explain() -> ExplainRequest:
        client.post(
            f"/api/chapters/{chapter_id}/explain", json={"passage": "Texte", "mode": "simpler"}
        )
        request = fake_provider.requests[-1]
        assert isinstance(request, ExplainRequest)
        return request

    assert explain().adaptations == ""
    client.patch(
        f"/api/students/{student['id']}",
        json={
            "adaptation_codes": ["dyspraxie", "tdah", "dyspraxie"],
            "adaptation_notes": " anxieux ",
        },
    )
    [updated] = client.get("/api/students").json()
    assert updated["adaptation_codes"] == ["dyspraxie", "tdah"]
    text = explain().adaptations
    assert text.startswith("Particularités de l'élève, à respecter : dyspraxique")
    assert "trouble de l'attention" in text
    assert "<particularites>anxieux</particularites>" in text


def test_adaptation_list_and_validation(client: TestClient) -> None:
    ids = [a["id"] for a in client.get("/api/adaptations").json()]
    assert "dyslexie" in ids
    bad = client.post("/api/students", json={"name": "X", "adaptation_codes": ["magie"]})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "unknown_adaptation"


def test_chapters_are_private_to_their_student(client: TestClient, chapter_id: int) -> None:
    """Un chapitre (et tout ce qui en dépend) n'est visible que de son élève."""
    other = {"X-Student-Id": str(client.post("/api/students", json={"name": "Léa"}).json()["id"])}
    base = f"/api/chapters/{chapter_id}"
    for path in ("", "/notes", "/notes/versions", "/photos"):
        assert client.get(base + path).status_code == 200, path
    for path in ("", "/notes", "/course", "/notes/versions", "/photos", "/export.md", "/quiz"):
        response = client.get(base + path, headers=other)
        assert response.status_code == 404, path
        assert response.json()["error"]["message"] == "Ce chapitre n'existe pas.", path
    assert client.put(f"{base}/notes", json={"raw_text": "x"}, headers=other).status_code == 404
    assert client.delete(base, headers=other).status_code == 404
    assert client.delete(base).status_code == 204
    assert client.post(f"/api/trash/{chapter_id}/restore", headers=other).status_code == 404
    assert client.delete(f"/api/trash/{chapter_id}", headers=other).status_code == 404
    assert client.post(f"/api/trash/{chapter_id}/restore").status_code == 200


def test_student_cookie_is_used_for_plain_requests(client: TestClient, chapter_id: int) -> None:
    """Les images demandées par le navigateur n'ont pas d'en-tête : le cookie le remplace."""
    other = client.post("/api/students", json={"name": "Léa"}).json()["id"]
    client.cookies.set("noteclaire_student", str(other))
    assert client.get(f"/api/chapters/{chapter_id}/photos").status_code == 404
    client.cookies.set("noteclaire_student", "1")
    assert client.get(f"/api/chapters/{chapter_id}/photos").status_code == 200
