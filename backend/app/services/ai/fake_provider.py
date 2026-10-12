from collections import deque

from app.services.ai.base import (
    AIProvider,
    AIProviderError,
    AIResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    AnalyzeResult,
    CourseRequest,
    ExplainRequest,
    ExplainResult,
    FigureBox,
    FigureLocations,
    FiguresRequest,
    PhotoRequest,
    PhotoResult,
    QuizQuestion,
    QuizResult,
    RedrawRequest,
    RedrawResult,
    RevisionSheetResult,
    SchemaArrow,
    SchemaText,
    StructureRequest,
    StructureResponse,
    StructureResult,
)

type Outcome = (
    StructureResponse
    | AnalyzeResponse
    | AIResponse[RevisionSheetResult]
    | AIResponse[QuizResult]
    | AIResponse[ExplainResult]
    | AIResponse[PhotoResult]
    | AIResponse[FigureLocations]
    | AIResponse[RedrawResult]
    | AIProviderError
)


class FakeProvider(AIProvider):
    """Provider sans réseau, pour les tests et le développement (AI_PROVIDER=fake).

    Sans réponses préparées, il renvoie les notes telles quelles sous un titre,
    et aucune suggestion.
    """

    name = "fake"
    model = "fake"

    def __init__(self, responses: list[Outcome] | None = None) -> None:
        self.responses: deque[Outcome] = deque(responses or [])
        self.requests: list[
            StructureRequest
            | AnalyzeRequest
            | CourseRequest
            | ExplainRequest
            | PhotoRequest
            | FiguresRequest
            | RedrawRequest
        ] = []

    async def structure_course(self, request: StructureRequest) -> StructureResponse:
        self.requests.append(request)
        if self.responses:
            return self._next(StructureResult)
        content = f"# {request.chapter}\n\n{request.raw_notes.strip()}\n"
        return AIResponse(StructureResult(clean_course=content), 0, 0)

    async def analyze_course(self, request: AnalyzeRequest) -> AnalyzeResponse:
        self.requests.append(request)
        if self.responses:
            return self._next(AnalyzeResult)
        return AIResponse(AnalyzeResult(suggestions=[]), 0, 0)

    async def generate_revision_sheet(
        self, request: CourseRequest
    ) -> AIResponse[RevisionSheetResult]:
        self.requests.append(request)
        if self.responses:
            return self._next(RevisionSheetResult)
        sheet = f"# À retenir : {request.chapter}\n\n{request.course.strip()}\n"
        return AIResponse(RevisionSheetResult(content_markdown=sheet), 0, 0)

    async def generate_quiz(self, request: CourseRequest) -> AIResponse[QuizResult]:
        self.requests.append(request)
        if self.responses:
            return self._next(QuizResult)
        excerpt = request.course.strip().splitlines()[0]
        question = QuizQuestion(
            type="true_false",
            question=f"Ce cours porte sur « {request.chapter} ».",
            choices=[],
            answer="Vrai",
            explanation="C'est le titre du chapitre.",
            course_excerpt=excerpt,
        )
        return AIResponse(QuizResult(questions=[question]), 0, 0)

    async def explain(self, request: ExplainRequest) -> AIResponse[ExplainResult]:
        self.requests.append(request)
        if self.responses:
            return self._next(ExplainResult)
        if request.mode == "question":
            result = ExplainResult(text=f"Que signifie « {request.passage} » ?", answer="Relis-le.")
        else:
            result = ExplainResult(text=f"Autrement dit : {request.passage}", answer="")
        return AIResponse(result, 0, 0)

    async def transcribe_photo(self, request: PhotoRequest) -> AIResponse[PhotoResult]:
        self.requests.append(request)
        if self.responses:
            return self._next(PhotoResult)
        return AIResponse(PhotoResult(text="texte lu sur la photo", uncertain=[]), 0, 0)

    async def locate_figures(self, request: FiguresRequest) -> AIResponse[FigureLocations]:
        self.requests.append(request)
        if self.responses:
            return self._next(FigureLocations)
        # Un rectangle au milieu de la photo pour chaque schéma demandé.
        boxes = [
            FigureBox(x_min=100, y_min=300, x_max=900, y_max=600) for _ in request.descriptions
        ]
        return AIResponse(FigureLocations(boxes=boxes), 0, 0)

    async def redraw_schema(self, request: RedrawRequest) -> AIResponse[RedrawResult]:
        self.requests.append(request)
        if self.responses:
            return self._next(RedrawResult)
        scene = RedrawResult(
            inventory=["une flèche, pointe à la fin"],
            texts=[SchemaText(x=10, y=40, text="propre", size=26, color="bleu")],
            arrows=[
                SchemaArrow(d="M 10 60 L 90 60", head_start=False, head_end=True, color="vert")
            ],
            lines=[],
            corrections=[],
        )
        return AIResponse(scene, 0, 0)

    def _next[T](self, expected: type[T]) -> AIResponse[T]:
        response = self.responses.popleft()
        if isinstance(response, AIProviderError):
            raise response
        assert isinstance(response.result, expected)
        return response  # type: ignore[return-value]
