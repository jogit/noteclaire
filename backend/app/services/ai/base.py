from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal

from pydantic import BaseModel, Field, field_validator

from app.errors import AppError
from app.levels import DEFAULT_LEVEL, prompt_label

DEFAULT_LABEL = prompt_label(DEFAULT_LEVEL)

# Les modèles envoyés à OpenAI comme schéma (structured outputs) n'utilisent pas de contraintes
# minLength / minimum / maximum, non prises en charge : elles sont vérifiées par des validateurs.

SuggestionType = Literal[
    "correction", "missing_information", "clarification", "addition", "warning"
]


class StructureResult(BaseModel):
    """Réponse de l'opération `structure` (SPEC §14)."""

    clean_course: str = Field(description="Le cours remis au propre, en Markdown.")

    @field_validator("clean_course")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("cours vide")
        return value


class SuggestionItem(BaseModel):
    type: SuggestionType
    original_text: str = Field(description="Extrait exact du cours, ou vide.")
    suggested_text: str
    reason: str
    confidence: float = Field(description="Entre 0 et 1.")
    reference_title: str = Field(
        description="Titre exact du document de référence utilisé, ou vide si aucun."
    )

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return min(1.0, max(0.0, value))


class AnalyzeResult(BaseModel):
    """Réponse de l'opération `analyze` (SPEC §14)."""

    suggestions: list[SuggestionItem]


class RevisionSheetResult(BaseModel):
    """Fiche de révision (SPEC §25)."""

    content_markdown: str = Field(description="La fiche de révision, en Markdown.")

    @field_validator("content_markdown")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fiche vide")
        return value


class FigureBox(BaseModel):
    """Rectangle d'un schéma sur la photo : de 0 (gauche ou haut) à 1000 (droite ou bas)."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int


class FigureLocations(BaseModel):
    boxes: list[FigureBox] = Field(
        description="Un rectangle par schéma demandé, dans le même ordre."
    )


SchemaColor = Literal["noir", "bleu", "vert", "rouge"]
COLOR_HELP = "Couleur de l'encre de l'élève pour cet élément (noir : crayon ou stylo noir)."


class SchemaText(BaseModel):
    x: float = Field(description="Début du texte (px, depuis la gauche de l'image).")
    y: float = Field(description="Ligne de base du texte (px, depuis le haut de l'image).")
    text: str = Field(description="Texte recopié ; indice « _{2} » et exposant « ^{2+} ».")
    size: float = Field(description="Hauteur des lettres en px (au moins 22).")
    color: SchemaColor = Field(description=COLOR_HELP)


class SchemaArrow(BaseModel):
    d: str = Field(description="Tracé SVG (M, L, C, Q…) en px, du DÉBUT vers la FIN de la flèche.")
    head_start: bool = Field(description="Pointe de flèche dessinée au DÉBUT du tracé ?")
    head_end: bool = Field(description="Pointe de flèche dessinée à la FIN du tracé ?")
    color: SchemaColor = Field(description=COLOR_HELP)


class SchemaLine(BaseModel):
    d: str = Field(description="Tracé SVG (M, L, C, Q, A…) d'un trait sans flèche.")
    color: SchemaColor = Field(description=COLOR_HELP)


class RedrawResult(BaseModel):
    """Un schéma manuscrit décrit par ses éléments ; le serveur en fait le dessin (SVG)."""

    inventory: list[str] = Field(
        description="Une ligne par flèche vue : d'où à où, pointe au début ? pointe à la fin ?"
    )
    texts: list[SchemaText]
    arrows: list[SchemaArrow]
    lines: list[SchemaLine]
    corrections: list[str] = Field(
        description="Erreurs manifestes corrigées dans le dessin, ou doutes signalés, chacune "
        "expliquée à l'élève en une phrase simple ; liste vide s'il n'y en a pas."
    )


QuestionType = Literal["qcm", "short", "true_false"]


class QuizQuestion(BaseModel):
    type: QuestionType
    question: str
    choices: list[str] = Field(description="Propositions du QCM ; liste vide sinon.")
    answer: str = Field(description="Bonne réponse (pour un QCM : une des propositions).")
    explanation: str
    course_excerpt: str = Field(description="Extrait exact du cours qui justifie la réponse.")


class QuizResult(BaseModel):
    """Quiz (SPEC §26)."""

    questions: list[QuizQuestion]


@dataclass(frozen=True)
class StructureRequest:
    subject: str
    chapter: str
    raw_notes: str
    level: str = DEFAULT_LABEL
    adaptations: str = ""


@dataclass(frozen=True)
class AnalyzeRequest:
    subject: str
    chapter: str
    course: str
    reference_context: str
    reference_titles: tuple[str, ...] = ()
    # Suggestions déjà refusées par l'élève, à ne pas reproposer (texte prêt pour le prompt).
    rejected: str = ""
    level: str = DEFAULT_LABEL
    adaptations: str = ""


class ExplainResult(BaseModel):
    """Réponse de « Je n'ai pas compris » (SPEC §19)."""

    text: str = Field(description="L'explication, en Markdown.")
    answer: str = Field(description="Réponse de la question de vérification, ou vide.")

    @field_validator("text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("explication vide")
        return value


ExplainMode = Literal["simpler", "example", "question"]


class UncertainSpot(BaseModel):
    """Passage difficile à lire, repéré par [?] dans le texte lu sur la photo."""

    guess: str = Field(description="Meilleure lecture, ou vide si illisible.")
    options: list[str] = Field(description="0 à 3 autres lectures plausibles.")


class PhotoResult(BaseModel):
    """Texte lu sur une photo de notes manuscrites."""

    text: str = Field(description="Le texte manuscrit recopié fidèlement, ou vide.")
    uncertain: list[UncertainSpot] = Field(description="Un élément par [?], dans l'ordre.")


@dataclass(frozen=True)
class PhotoRequest:
    subject: str
    chapter: str
    image_data_url: str  # JPEG nettoyé (sans métadonnées), en data URL
    level: str = DEFAULT_LABEL
    adaptations: str = ""


@dataclass(frozen=True)
class FiguresRequest:
    """Où sont, sur la photo, les schémas décrits (dans l'ordre) ?"""

    descriptions: tuple[str, ...]
    image_data_url: str


@dataclass(frozen=True)
class RedrawRequest:
    """Redessiner un schéma (image de `width` x `height` px) ; `context` = notes de l'élève."""

    width: int
    height: int
    image_data_url: str
    context: str
    # Correction demandée par l'élève sur une première version : sa description et la remarque.
    previous_scene: str = ""
    remark: str = ""


@dataclass(frozen=True)
class ExplainRequest:
    subject: str
    chapter: str
    course: str
    passage: str
    mode: ExplainMode
    level: str = DEFAULT_LABEL
    adaptations: str = ""


@dataclass(frozen=True)
class CourseRequest:
    """Demande portant uniquement sur le cours courant (fiche, quiz)."""

    subject: str
    chapter: str
    course: str
    level: str = DEFAULT_LABEL
    adaptations: str = ""


@dataclass(frozen=True)
class AIResponse[T]:
    result: T
    input_tokens: int | None = None
    output_tokens: int | None = None


StructureResponse = AIResponse[StructureResult]
AnalyzeResponse = AIResponse[AnalyzeResult]


class AIProviderError(AppError):
    """Erreur d'un provider IA, traduite en message compréhensible par le frontend."""

    MESSAGES: ClassVar[dict[str, tuple[str, int]]] = {
        "ai_not_configured": ("L'IA n'est pas configurée (clé API manquante).", 503),
        "ai_timeout": ("L'IA a mis trop de temps à répondre. Réessaie.", 504),
        "ai_invalid_key": ("La clé API de l'IA est invalide.", 502),
        "ai_quota_exceeded": ("Le crédit du compte IA est épuisé.", 502),
        "ai_rate_limited": ("L'IA est très sollicitée. Réessaie dans un instant.", 503),
        "ai_unavailable": ("Le service d'IA est indisponible. Réessaie plus tard.", 503),
        "ai_invalid_response": ("L'IA a renvoyé une réponse inutilisable. Réessaie.", 502),
        "ai_local_unavailable": (
            "Le modèle local ne répond pas. Vérifie qu'Ollama ou LM Studio est lancé.",
            503,
        ),
        "ai_local_model_missing": (
            "Le modèle local demandé n'est pas installé (voir LOCAL_AI_MODEL).",
            503,
        ),
        "chatgpt_not_connected": (
            "Connecte ton compte ChatGPT dans les Réglages pour utiliser l'IA.",
            409,
        ),
        "chatgpt_reauth": (
            "La connexion ChatGPT a expiré : reconnecte-toi dans les Réglages.",
            409,
        ),
        "chatgpt_auth_unavailable": (
            "Le service de connexion ChatGPT ne répond pas. Réessaie dans un instant.",
            503,
        ),
        "chatgpt_usage_limit": (
            "La limite d'utilisation de ton abonnement ChatGPT pour NoteClaire est atteinte. "
            "Tu peux la régler dans ChatGPT → Réglages → Utilisation.",
            429,
        ),
        "chatgpt_not_eligible": (
            "Ce compte ChatGPT ne permet pas d'utiliser l'abonnement dans d'autres applications "
            "(offre Plus ou Pro nécessaire).",
            403,
        ),
        "chatgpt_model_unavailable": (
            "Ce modèle n'est pas disponible avec ton abonnement : choisis-en un autre dans les "
            "Réglages.",
            409,
        ),
        "chatgpt_storage": (
            "La connexion ChatGPT enregistrée est illisible : reconnecte-toi.",
            409,
        ),
    }

    def __init__(self, code: str) -> None:
        message, status_code = self.MESSAGES[code]
        super().__init__(code, message, status_code)


class AIProvider(ABC):
    name: str
    model: str
    # Un modèle local est gratuit : il n'est pas soumis au budget IA.
    paid: bool = True

    @abstractmethod
    async def structure_course(self, request: StructureRequest) -> StructureResponse:
        """Nettoie et structure les notes, sans ajouter de contenu."""

    @abstractmethod
    async def analyze_course(self, request: AnalyzeRequest) -> AnalyzeResponse:
        """Propose des suggestions sans modifier le cours."""

    @abstractmethod
    async def generate_revision_sheet(
        self, request: CourseRequest
    ) -> AIResponse[RevisionSheetResult]:
        """Fiche de révision tirée uniquement du cours."""

    @abstractmethod
    async def generate_quiz(self, request: CourseRequest) -> AIResponse[QuizResult]:
        """Quiz tiré uniquement du cours."""

    @abstractmethod
    async def explain(self, request: ExplainRequest) -> AIResponse[ExplainResult]:
        """Réexplique un passage que l'élève n'a pas compris."""

    @abstractmethod
    async def transcribe_photo(self, request: PhotoRequest) -> AIResponse[PhotoResult]:
        """Recopie fidèlement le texte manuscrit d'une photo de notes."""

    @abstractmethod
    async def locate_figures(self, request: FiguresRequest) -> AIResponse[FigureLocations]:
        """Rectangle de chacun des schémas décrits, sur la photo."""

    @abstractmethod
    async def redraw_schema(self, request: RedrawRequest) -> AIResponse[RedrawResult]:
        """Redessine proprement, en SVG, un schéma manuscrit."""
