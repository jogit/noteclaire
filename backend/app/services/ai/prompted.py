from abc import abstractmethod

from pydantic import BaseModel

from app.prompts import escape_data, render_prompt
from app.services.ai.base import (
    AIProvider,
    AIResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResult,
    CourseRequest,
    ExplainRequest,
    ExplainResult,
    FigureLocations,
    FiguresRequest,
    PhotoRequest,
    PhotoResult,
    QuizResult,
    RedrawRequest,
    RedrawResult,
    RevisionSheetResult,
    StructureRequest,
    StructureResponse,
    StructureResult,
)

EXPLAIN_REQUESTS = {
    "simpler": "Explique ce passage plus simplement, avec des mots de tous les jours.",
    "example": "Donne un exemple concret et simple qui illustre ce passage.",
    "question": (
        "Pose une seule question courte pour vérifier que l'élève a compris ce passage. "
        'Ne donne pas la réponse dans "text".'
    ),
}


class PromptedProvider(AIProvider):
    """Construit les prompts ; chaque provider n'implémente que l'appel structuré."""

    @abstractmethod
    async def _parse[T: BaseModel](
        self, prompt: str, schema: type[T], images: tuple[str, ...] = ()
    ) -> AIResponse[T]:
        """Envoie le prompt (avec le prompt système et d'éventuelles images en data URL)
        et valide la réponse avec le schéma."""

    async def structure_course(self, request: StructureRequest) -> StructureResponse:
        prompt = render_prompt(
            "structure",
            subject=request.subject,
            level=request.level,
            chapter=request.chapter,
            raw_notes=request.raw_notes,
            adaptations=request.adaptations,
        )
        return await self._parse(prompt, StructureResult)

    async def analyze_course(self, request: AnalyzeRequest) -> AnalyzeResponse:
        prompt = render_prompt(
            "analyze",
            subject=request.subject,
            level=request.level,
            chapter=request.chapter,
            cleaned_course=request.course,
            reference_context=request.reference_context,
            rejected=request.rejected or "Aucune.",
            adaptations=request.adaptations,
        )
        return await self._parse(prompt, AnalyzeResult)

    async def generate_revision_sheet(
        self, request: CourseRequest
    ) -> AIResponse[RevisionSheetResult]:
        prompt = render_prompt(
            "revision_sheet",
            subject=request.subject,
            level=request.level,
            adaptations=request.adaptations,
            chapter=request.chapter,
            course=request.course,
        )
        return await self._parse(prompt, RevisionSheetResult)

    async def generate_quiz(self, request: CourseRequest) -> AIResponse[QuizResult]:
        prompt = render_prompt(
            "quiz",
            subject=request.subject,
            level=request.level,
            chapter=request.chapter,
            course=request.course,
            adaptations=request.adaptations,
        )
        return await self._parse(prompt, QuizResult)

    async def explain(self, request: ExplainRequest) -> AIResponse[ExplainResult]:
        prompt = render_prompt(
            "explain",
            subject=request.subject,
            level=request.level,
            chapter=request.chapter,
            course=request.course,
            adaptations=request.adaptations,
            passage=request.passage,
            request=EXPLAIN_REQUESTS[request.mode],
        )
        return await self._parse(prompt, ExplainResult)

    async def transcribe_photo(self, request: PhotoRequest) -> AIResponse[PhotoResult]:
        prompt = render_prompt(
            "photo",
            subject=request.subject,
            level=request.level,
            chapter=request.chapter,
            adaptations=request.adaptations,
        )
        return await self._parse(prompt, PhotoResult, images=(request.image_data_url,))

    async def locate_figures(self, request: FiguresRequest) -> AIResponse[FigureLocations]:
        listing = "\n".join(f"{i}. {d}" for i, d in enumerate(request.descriptions, start=1))
        prompt = render_prompt("figures", descriptions=listing)
        return await self._parse(prompt, FigureLocations, images=(request.image_data_url,))

    async def redraw_schema(self, request: RedrawRequest) -> AIResponse[RedrawResult]:
        correction = ""
        if request.remark:
            correction = (
                "Une première version a déjà été proposée (description JSON ci-dessous). L'élève "
                f"la trouve imparfaite : <remarque>{escape_data(request.remark)}</remarque>. "
                "Corrige ce point, en gardant le reste tel quel, et compare toujours avec "
                "l'image de l'élève.\n\n"
                f"{request.previous_scene}\n\n"
            )
        prompt = render_prompt(
            "redraw",
            width=str(request.width),
            height=str(request.height),
            context=request.context,
            correction=correction,
        )
        return await self._parse(prompt, RedrawResult, images=(request.image_data_url,))
