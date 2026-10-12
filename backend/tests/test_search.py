from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.search_service import MARK_END, MARK_START, build_query, reindex_all
from tests.conftest import structured


def search(client: TestClient, query: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = client.get("/api/search", params={"q": query}).json()
    return results


def test_build_query() -> None:
    assert build_query("Fonctions AFFINES") == '"fonctions"* AND "affines"*'
    assert build_query("équation") == '"equation"*'
    assert build_query(" ? ") == ""


def test_search_title_notes_and_course(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "le coefficient directeur", "# Cours\n\nOrdonnée à l'origine")

    assert [r["chapter_id"] for r in search(client, "affines")] == [chapter_id]  # titre
    assert [r["chapter_id"] for r in search(client, "mathematiques")] == [chapter_id]  # matière
    assert [r["chapter_id"] for r in search(client, "directeur")] == [chapter_id]  # notes
    assert [r["chapter_id"] for r in search(client, "ordonnee origine")] == [chapter_id]  # cours
    assert [r["chapter_id"] for r in search(client, "coef")] == [chapter_id]  # préfixe
    assert search(client, "photosynthese") == []
    assert search(client, "") == []


def test_snippet_is_highlighted(client: TestClient, chapter_id: int) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "la pente est a"})
    [result] = search(client, "pente")
    assert f"{MARK_START}pente{MARK_END}" in str(result["snippet"])


def test_index_follows_changes(client: TestClient, chapter_id: int) -> None:
    client.patch(f"/api/chapters/{chapter_id}", json={"title": "Vecteurs"})
    assert search(client, "affines") == []
    assert len(search(client, "vecteurs")) == 1

    client.delete(f"/api/chapters/{chapter_id}")
    assert search(client, "vecteurs") == []


def test_reindex_all(app: FastAPI, client: TestClient, chapter_id: int) -> None:
    with app.state.db.session_factory() as db:
        reindex_all(db)
    assert len(search(client, "affines")) == 1
