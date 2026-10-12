"""Fiches de révision et quiz, générés uniquement depuis le cours courant (SPEC §25, §26)."""

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.errors import NotFoundError
from app.levels import adaptations_text, prompt_label
from app.models import Course, Quiz, RevisionSheet
from app.prompts import (
    EXPLAIN_PROMPT_VERSION,
    QUIZ_PROMPT_VERSION,
    REVISION_SHEET_PROMPT_VERSION,
)
from app.services.ai.base import (
    AIProvider,
    AIProviderError,
    CourseRequest,
    ExplainMode,
    ExplainRequest,
    ExplainResult,
    QuizQuestion,
)
from app.services.ai_runs import run_ai
from app.services.chapter_service import get_chapter
from app.services.course_service import require_current_course, sha256
from app.services.figure_service import describe_schemas

logger = logging.getLogger(__name__)

TRUE_FALSE = ("Vrai", "Faux")
EXPLAIN_CONTEXT_CHARS = 6000


def _request(db: Session, settings: Settings, chapter_id: int) -> tuple[CourseRequest, Course]:
    chapter = get_chapter(db, chapter_id)
    course = require_current_course(db, chapter_id)
    request = CourseRequest(
        subject=chapter.subject.name,
        chapter=chapter.title,
        course=describe_schemas(settings, course.content_markdown),
        level=prompt_label(chapter.student.level),
        adaptations=adaptations_text(
            chapter.student.adaptation_codes, chapter.student.adaptation_notes
        ),
    )
    return request, course


def _hash(prompt_version: str, request: CourseRequest) -> str:
    return sha256(
        "\n".join(
            [
                prompt_version,
                request.subject,
                request.level,
                request.adaptations,
                request.chapter,
                request.course,
            ]
        )
    )


async def generate_revision_sheet(
    db: Session, settings: Settings, chapter_id: int, provider: AIProvider
) -> RevisionSheet:
    request, course = _request(db, settings, chapter_id)
    response, run = await run_ai(
        db,
        settings,
        lambda: provider.generate_revision_sheet(request),
        chapter_id=chapter_id,
        operation="revision_sheet",
        provider=provider.name,
        model=provider.model,
        prompt_version=REVISION_SHEET_PROMPT_VERSION,
        input_hash=_hash(REVISION_SHEET_PROMPT_VERSION, request),
        enforce_budget=provider.paid,
    )
    sheet = RevisionSheet(
        chapter_id=chapter_id,
        course_version_id=course.id,
        content_markdown=response.result.content_markdown,
        ai_run_id=run.id,
    )
    db.add(sheet)
    db.commit()
    return sheet


def latest_revision_sheet(db: Session, chapter_id: int) -> RevisionSheet:
    get_chapter(db, chapter_id)
    sheet = db.scalar(
        select(RevisionSheet)
        .where(RevisionSheet.chapter_id == chapter_id)
        .order_by(RevisionSheet.id.desc())
        .limit(1)
    )
    if sheet is None:
        raise NotFoundError("Aucune fiche de révision pour ce chapitre.")
    return sheet


def clean_questions(questions: list[QuizQuestion], course: str) -> list[QuizQuestion]:
    """Écarte les questions incohérentes ; ne garde un extrait que s'il vient du cours."""
    kept: list[QuizQuestion] = []
    for question in questions:
        if not question.question.strip() or not question.answer.strip():
            continue
        if question.type == "qcm":
            choices = list(dict.fromkeys(c.strip() for c in question.choices if c.strip()))
            if not 2 <= len(choices) <= 6 or question.answer.strip() not in choices:
                continue
            question = question.model_copy(
                update={"choices": choices, "answer": question.answer.strip()}
            )
        elif question.type == "true_false":
            answer = question.answer.strip().capitalize()
            if answer not in TRUE_FALSE:
                continue
            question = question.model_copy(update={"choices": list(TRUE_FALSE), "answer": answer})
        else:
            question = question.model_copy(update={"choices": []})
        if question.course_excerpt and question.course_excerpt not in course:
            question = question.model_copy(update={"course_excerpt": ""})
        kept.append(question)
    return kept


async def generate_quiz(
    db: Session, settings: Settings, chapter_id: int, provider: AIProvider
) -> Quiz:
    request, course = _request(db, settings, chapter_id)
    response, run = await run_ai(
        db,
        settings,
        lambda: provider.generate_quiz(request),
        chapter_id=chapter_id,
        operation="quiz",
        provider=provider.name,
        model=provider.model,
        prompt_version=QUIZ_PROMPT_VERSION,
        input_hash=_hash(QUIZ_PROMPT_VERSION, request),
        enforce_budget=provider.paid,
    )
    questions = clean_questions(response.result.questions, course.content_markdown)
    discarded = len(response.result.questions) - len(questions)
    if discarded:
        logger.info("quiz chapter=%s discarded=%s", chapter_id, discarded)
    if not questions:
        db.commit()  # garde la trace de l'appel
        raise AIProviderError("ai_invalid_response")
    quiz = Quiz(
        chapter_id=chapter_id,
        course_version_id=course.id,
        questions_json=json.dumps([q.model_dump() for q in questions], ensure_ascii=False),
        ai_run_id=run.id,
    )
    db.add(quiz)
    db.commit()
    return quiz


async def explain_passage(
    db: Session,
    settings: Settings,
    chapter_id: int,
    passage: str,
    mode: ExplainMode,
    provider: AIProvider,
) -> ExplainResult:
    """« Je n'ai pas compris » (SPEC §19) : rien n'est enregistré à part le journal AIRun."""
    course_request, _course = _request(db, settings, chapter_id)
    request = ExplainRequest(
        subject=course_request.subject,
        chapter=course_request.chapter,
        course=course_request.course[:EXPLAIN_CONTEXT_CHARS],
        passage=passage.strip(),
        mode=mode,
        level=course_request.level,
        adaptations=course_request.adaptations,
    )
    response, _run = await run_ai(
        db,
        settings,
        lambda: provider.explain(request),
        chapter_id=chapter_id,
        operation="explain",
        provider=provider.name,
        model=provider.model,
        prompt_version=EXPLAIN_PROMPT_VERSION,
        input_hash=sha256("\n".join([EXPLAIN_PROMPT_VERSION, mode, request.passage])),
        enforce_budget=provider.paid,
    )
    db.commit()
    return response.result


def latest_quiz(db: Session, chapter_id: int) -> Quiz:
    get_chapter(db, chapter_id)
    quiz = db.scalar(
        select(Quiz).where(Quiz.chapter_id == chapter_id).order_by(Quiz.id.desc()).limit(1)
    )
    if quiz is None:
        raise NotFoundError("Aucun quiz pour ce chapitre.")
    return quiz


def quiz_questions(quiz: Quiz) -> list[QuizQuestion]:
    return [QuizQuestion.model_validate(q) for q in json.loads(quiz.questions_json)]


def is_outdated(db: Session, chapter_id: int, course_version_id: int) -> bool:
    current = require_current_course(db, chapter_id)
    return current.id != course_version_id
