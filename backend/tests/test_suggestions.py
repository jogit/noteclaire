from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.ai.base import (
    AIProviderError,
    AIResponse,
    AnalyzeRequest,
    AnalyzeResult,
    SuggestionItem,
)
from app.services.ai.fake_provider import FakeProvider
from tests.conftest import structured

COURSE = (
    "# Fonctions affines\n\n"
    "Une fonction affine s'écrit $f(x) = ax + b$.\n\n"
    "- b est la pente\n"
    "- a est l'ordonnée à l'origine\n"
)


def item(**kwargs: Any) -> SuggestionItem:
    values: dict[str, Any] = {
        "type": "correction",
        "original_text": "b est la pente",
        "suggested_text": "a est le coefficient directeur",
        "reason": "La définition semble inversée.",
        "confidence": 0.9,
        "reference_title": "",
    } | kwargs
    return SuggestionItem(**values)


def analyze(
    client: TestClient, provider: FakeProvider, chapter_id: int, *items: SuggestionItem
) -> list[dict[str, Any]]:
    provider.responses.append(AIResponse(AnalyzeResult(suggestions=list(items)), 200, 40))
    response = client.post(f"/api/chapters/{chapter_id}/analyze")
    assert response.status_code == 201, response.text
    result: list[dict[str, Any]] = response.json()
    return result


def current_course(client: TestClient, chapter_id: int) -> dict[str, Any]:
    course: dict[str, Any] = client.get(f"/api/chapters/{chapter_id}/course").json()
    return course


@pytest.fixture
def chapter(client: TestClient, chapter_id: int) -> int:
    structured(client, chapter_id, "notes", COURSE)
    return chapter_id


def test_analyze_stores_suggestions_without_changing_course(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(client, fake_provider, chapter, item())

    assert suggestion["status"] == "pending"
    assert suggestion["confidence"] == 0.9
    assert current_course(client, chapter)["version"] == 1
    request = fake_provider.requests[-1]
    assert isinstance(request, AnalyzeRequest)
    assert request.course == COURSE
    assert client.get(f"/api/chapters/{chapter}/suggestions?status=pending").json() == [suggestion]


def test_analyze_requires_a_course(client: TestClient, chapter_id: int) -> None:
    assert client.post(f"/api/chapters/{chapter_id}/analyze").status_code == 404


def test_analyze_discards_unusable_suggestions(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    suggestions = analyze(
        client,
        fake_provider,
        chapter,
        item(original_text="texte absent du cours"),
        item(original_text="", type="correction"),
        item(original_text="b est la pente", suggested_text="b est la pente"),
        item(original_text="", type="addition", suggested_text="Complément."),
        item(original_text="", type="warning", suggested_text=""),
        item(confidence=7),
    )
    # Les plus importantes d'abord : correction, avertissement, complément.
    assert [(s["type"], s["confidence"]) for s in suggestions] == [
        ("correction", 1.0),
        ("warning", 0.9),
        ("addition", 0.9),
    ]


def test_analyze_keeps_only_the_four_most_important_suggestions(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    addition = item(original_text="", type="addition", suggested_text="Complément.")
    suggestions = analyze(
        client,
        fake_provider,
        chapter,
        addition,
        addition,
        addition,
        item(),
        item(),
        item(original_text="", type="warning", suggested_text=""),
    )
    assert [s["type"] for s in suggestions] == ["correction", "correction", "warning", "addition"]


def test_new_analysis_replaces_pending_suggestions(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [first] = analyze(client, fake_provider, chapter, item())
    analyze(client, fake_provider, chapter, item())
    statuses = {
        s["id"]: s["status"] for s in client.get(f"/api/chapters/{chapter}/suggestions").json()
    }
    assert statuses[first["id"]] == "outdated"
    assert list(statuses.values()).count("pending") == 1


def test_accept_correction_creates_a_version(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(client, fake_provider, chapter, item())

    response = client.post(f"/api/suggestions/{suggestion['id']}/accept")

    assert response.status_code == 200
    body = response.json()
    assert body["suggestion"]["status"] == "accepted"
    assert body["suggestion"]["decided_at"] is not None
    course = body["course"]
    assert course["version"] == 2
    assert course["origin"] == "suggestion_applied"
    assert course["has_manual_changes"] is True
    assert course["notes_changed"] is False
    assert "- a est le coefficient directeur\n- a est l'ordonnée" in course["content_markdown"]
    # La version précédente reste intacte.
    old = client.get(f"/api/chapters/{chapter}/course/versions/1").json()
    assert old["content_markdown"] == COURSE


def test_accept_addition_inserts_after_the_line(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(
        client,
        fake_provider,
        chapter,
        item(type="addition", original_text="ax + b", suggested_text="Si b = 0, f est linéaire."),
    )
    course = client.post(f"/api/suggestions/{suggestion['id']}/accept").json()["course"]
    assert (
        "$f(x) = ax + b$.\n\nSi b = 0, f est linéaire.\n\n- b est la pente"
        in (course["content_markdown"])
    )


def test_accept_addition_without_anchor_appends(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(
        client,
        fake_provider,
        chapter,
        item(type="addition", original_text="", suggested_text="Fin."),
    )
    course = client.post(f"/api/suggestions/{suggestion['id']}/accept").json()["course"]
    assert course["content_markdown"].endswith("l'origine\n\nFin.\n")


def test_accept_warning_does_not_change_course(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(client, fake_provider, chapter, item(type="warning", suggested_text=""))
    body = client.post(f"/api/suggestions/{suggestion['id']}/accept").json()
    assert body["suggestion"]["status"] == "accepted"
    assert body["course"]["version"] == 1


def test_ambiguous_passage_asks_which_occurrence(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(
        client, fake_provider, chapter, item(original_text="est l", suggested_text="EST L")
    )
    url = f"/api/suggestions/{suggestion['id']}/accept"

    response = client.post(url)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "suggestion_ambiguous"
    occurrences = error["details"]["occurrences"]
    assert len(occurrences) == 2
    assert occurrences[1]["before"].endswith("- a ")

    assert client.post(url, json={"occurrence": 5}).status_code == 422
    course = client.post(url, json={"occurrence": 1}).json()["course"]
    assert "- b est la pente\n- a EST L'ordonnée" in course["content_markdown"]


def test_suggestion_becomes_outdated_when_passage_disappears(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [suggestion] = analyze(client, fake_provider, chapter, item())
    client.put(
        f"/api/chapters/{chapter}/course",
        json={"content_markdown": COURSE.replace("b est la pente", "b est autre chose")},
    )

    pending = client.get(f"/api/chapters/{chapter}/suggestions?status=pending").json()
    assert pending == []
    response = client.post(f"/api/suggestions/{suggestion['id']}/accept")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "suggestion_not_pending"


def test_accept_on_changed_course_marks_outdated(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    first, second = analyze(
        client,
        fake_provider,
        chapter,
        item(),
        item(original_text="b est la", suggested_text="b vaut"),
    )
    client.post(f"/api/suggestions/{first['id']}/accept")

    # Le passage visé par la seconde suggestion a disparu avec la première.
    response = client.get(f"/api/chapters/{chapter}/suggestions").json()
    assert {s["id"]: s["status"] for s in response}[second["id"]] == "outdated"


def test_reject(client: TestClient, fake_provider: FakeProvider, chapter: int) -> None:
    [suggestion] = analyze(client, fake_provider, chapter, item())

    response = client.post(f"/api/suggestions/{suggestion['id']}/reject")

    assert response.json()["status"] == "rejected"
    assert current_course(client, chapter)["version"] == 1
    again = client.post(f"/api/suggestions/{suggestion['id']}/reject")
    assert again.status_code == 409


def test_unknown_suggestion(client: TestClient) -> None:
    assert client.post("/api/suggestions/999/accept").status_code == 404


def test_analyze_error_keeps_pending_suggestions(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    analyze(client, fake_provider, chapter, item())
    fake_provider.responses.append(AIProviderError("ai_timeout"))
    assert client.post(f"/api/chapters/{chapter}/analyze").status_code == 504
    assert len(client.get(f"/api/chapters/{chapter}/suggestions?status=pending").json()) == 1


def test_rejected_suggestions_are_not_proposed_again(
    client: TestClient, fake_provider: FakeProvider, chapter: int
) -> None:
    [refused] = analyze(client, fake_provider, chapter, item())
    client.post(f"/api/suggestions/{refused['id']}/reject")

    # L'IA repropose la même chose (espaces et majuscules près) et une nouvelle idée.
    again = item(suggested_text="  A est le   coefficient directeur ")
    other = item(original_text="a est l'ordonnée", suggested_text="b est l'ordonnée")
    suggestions = analyze(client, fake_provider, chapter, again, other)

    assert [s["suggested_text"] for s in suggestions] == ["b est l'ordonnée"]
    request = fake_provider.requests[-1]
    assert isinstance(request, AnalyzeRequest)
    assert "« b est la pente » → « a est le coefficient directeur »" in request.rejected
