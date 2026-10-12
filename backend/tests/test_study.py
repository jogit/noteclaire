from typing import Any

from fastapi.testclient import TestClient

from app.services.ai.base import (
    AIProviderError,
    AIResponse,
    CourseRequest,
    ExplainRequest,
    QuizQuestion,
    QuizResult,
    RevisionSheetResult,
)
from app.services.ai.fake_provider import FakeProvider
from app.services.study_service import clean_questions
from tests.conftest import structured

COURSE = (
    "# Fonctions affines\n\n"
    "Une fonction affine s'écrit $f(x) = ax + b$.\n\n"
    "a est le coefficient directeur.\n"
)


def question(**kwargs: Any) -> QuizQuestion:
    values: dict[str, Any] = {
        "type": "qcm",
        "question": "Comment s'appelle a ?",
        "choices": ["Le coefficient directeur", "L'ordonnée à l'origine", "La pente nulle"],
        "answer": "Le coefficient directeur",
        "explanation": "C'est écrit dans le cours.",
        "course_excerpt": "a est le coefficient directeur.",
    } | kwargs
    return QuizQuestion(**values)


def test_clean_questions() -> None:
    kept = clean_questions(
        [
            question(),
            question(answer="Absente des choix"),
            question(choices=["Seule"], answer="Seule"),
            question(type="true_false", choices=["x"], answer="vrai"),
            question(type="true_false", answer="Peut-être"),
            question(type="short", choices=["inutile"], answer="ax + b"),
            question(question="  "),
            question(course_excerpt="Phrase inventée."),
        ],
        COURSE,
    )
    assert [(q.type, q.answer) for q in kept] == [
        ("qcm", "Le coefficient directeur"),
        ("true_false", "Vrai"),
        ("short", "ax + b"),
        ("qcm", "Le coefficient directeur"),
    ]
    assert kept[1].choices == ["Vrai", "Faux"]
    assert kept[2].choices == []
    assert kept[3].course_excerpt == ""


def test_revision_sheet_uses_only_current_course(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    structured(client, chapter_id, "notes", COURSE)
    fake_provider.responses.append(
        AIResponse(RevisionSheetResult(content_markdown="# À retenir\n\n- **a** : coefficient"))
    )

    response = client.post(f"/api/chapters/{chapter_id}/revision-sheet")

    assert response.status_code == 201
    sheet = response.json()
    assert sheet["content_markdown"].startswith("# À retenir")
    assert (sheet["course_version"], sheet["outdated"]) == (1, False)
    request = fake_provider.requests[-1]
    assert isinstance(request, CourseRequest)
    assert request.course == COURSE
    assert client.get(f"/api/chapters/{chapter_id}/revision-sheet").json() == sheet


def test_revision_sheet_becomes_outdated(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", COURSE)
    client.post(f"/api/chapters/{chapter_id}/revision-sheet")
    client.put(f"/api/chapters/{chapter_id}/course", json={"content_markdown": "# Nouveau"})
    assert client.get(f"/api/chapters/{chapter_id}/revision-sheet").json()["outdated"] is True


def test_study_requires_course(client: TestClient, chapter_id: int) -> None:
    assert client.post(f"/api/chapters/{chapter_id}/revision-sheet").status_code == 404
    assert client.post(f"/api/chapters/{chapter_id}/quiz").status_code == 404
    assert client.get(f"/api/chapters/{chapter_id}/revision-sheet").status_code == 404
    assert client.get(f"/api/chapters/{chapter_id}/quiz").status_code == 404


def test_quiz_keeps_valid_questions(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    structured(client, chapter_id, "notes", COURSE)
    fake_provider.responses.append(
        AIResponse(QuizResult(questions=[question(), question(answer="Faux choix")]))
    )

    quiz = client.post(f"/api/chapters/{chapter_id}/quiz").json()

    assert len(quiz["questions"]) == 1
    assert quiz["questions"][0]["choices"][0] == "Le coefficient directeur"
    assert client.get(f"/api/chapters/{chapter_id}/quiz").json() == quiz


def test_quiz_without_valid_question_is_an_error(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    structured(client, chapter_id, "notes", COURSE)
    fake_provider.responses.append(AIResponse(QuizResult(questions=[question(answer="?")])))
    response = client.post(f"/api/chapters/{chapter_id}/quiz")
    assert response.status_code == 502
    assert client.get(f"/api/chapters/{chapter_id}/quiz").status_code == 404


def test_quiz_provider_error(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    structured(client, chapter_id, "notes", COURSE)
    fake_provider.responses.append(AIProviderError("ai_timeout"))
    assert client.post(f"/api/chapters/{chapter_id}/quiz").status_code == 504


def test_export_markdown(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", COURSE)

    response = client.get(f"/api/chapters/{chapter_id}/export.md")

    assert response.headers["content-type"].startswith("text/markdown")
    assert (
        'filename="mathematiques-fonctions-affines.md"' in response.headers["content-disposition"]
    )
    assert "**Mathématiques** · Fonctions affines" in response.text
    assert response.text.endswith("a est le coefficient directeur.\n")


def test_explain_passage(client: TestClient, fake_provider: FakeProvider, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", COURSE)

    response = client.post(
        f"/api/chapters/{chapter_id}/explain",
        json={"passage": " coefficient directeur ", "mode": "question"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "text": "Que signifie « coefficient directeur » ?",
        "answer": "Relis-le.",
    }
    request = fake_provider.requests[-1]
    assert isinstance(request, ExplainRequest)
    assert (request.passage, request.mode, request.course) == (
        "coefficient directeur",
        "question",
        COURSE,
    )
    # Rien n'est ajouté au cours.
    assert client.get(f"/api/chapters/{chapter_id}/course").json()["version"] == 1


def test_explain_validation(client: TestClient, chapter_id: int) -> None:
    structured(client, chapter_id, "notes", COURSE)
    url = f"/api/chapters/{chapter_id}/explain"
    assert client.post(url, json={"passage": "", "mode": "simpler"}).status_code == 422
    assert client.post(url, json={"passage": "x", "mode": "autre"}).status_code == 422
    assert client.post(url, json={"passage": "x" * 2001, "mode": "simpler"}).status_code == 422


def test_quiz_export_to_anki(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    assert client.get(f"/api/chapters/{chapter_id}/quiz/anki.txt").status_code == 404
    structured(client, chapter_id, "notes", COURSE)
    fake_provider.responses.append(AIResponse(QuizResult(questions=[question()])))
    client.post(f"/api/chapters/{chapter_id}/quiz")

    response = client.get(f"/api/chapters/{chapter_id}/quiz/anki.txt")

    assert response.headers["content-type"].startswith("text/plain")
    assert (
        'filename="mathematiques-fonctions-affines-anki.txt"'
        in response.headers["content-disposition"]
    )
    lines = response.text.splitlines()
    assert lines[:3] == ["#separator:tab", "#html:true", "#tags column:3"]
    assert lines[3] == "#deck:NoteClaire::Mathématiques::Fonctions affines"
    [card] = lines[4:]
    front, back, tag = card.split("\t")
    assert "Le coefficient directeur" in front and "<br>" in front
    assert back.startswith("<b>Le coefficient directeur</b>")
    assert "Dans ton cours" in back
    assert tag == "mathematiques"
