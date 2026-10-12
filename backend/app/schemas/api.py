from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator


def _as_utc(value: datetime) -> datetime:
    # SQLite ne conserve pas le fuseau : les dates sont stockées en UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


UTCDatetime = Annotated[datetime, AfterValidator(_as_utc)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SubjectOut(ORMModel):
    id: int
    name: str
    slug: str
    enabled: bool = True  # activée pour l'élève courant
    usual_for: list[str] = []  # classes où cette matière est habituelle
    chapter_count: int = 0


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)


class StudentOut(ORMModel):
    id: int
    name: str
    level: str
    adaptation_codes: list[str]
    adaptation_notes: str
    subject_ids: list[int] = []  # matières suivies (remplies par l'API)

    @field_validator("adaptation_codes", mode="before")
    @classmethod
    def split_codes(cls, value: object) -> object:
        return [c for c in value.split(",") if c] if isinstance(value, str) else value


class AdaptationOut(BaseModel):
    id: str
    name: str


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: str = "seconde"
    adaptation_codes: list[str] = Field(default_factory=list, max_length=20)
    adaptation_notes: str = Field(default="", max_length=300)


class StudentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    level: str | None = None
    adaptation_codes: list[str] | None = Field(default=None, max_length=20)
    adaptation_notes: str | None = Field(default=None, max_length=300)


class LevelOut(BaseModel):
    id: str
    name: str


class ChapterCreate(BaseModel):
    subject_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    school_year: str = Field(default="", max_length=20)


class ChapterUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    school_year: str | None = Field(default=None, max_length=20)


class ChapterProgressOut(BaseModel):
    notes_words: int
    course_version: int | None
    notes_changed: bool
    pending_suggestions: int
    has_revision_sheet: bool
    has_quiz: bool


class ChapterOut(ORMModel):
    id: int
    subject_id: int
    subject: SubjectOut
    title: str
    description: str
    school_year: str
    created_at: UTCDatetime
    updated_at: UTCDatetime
    progress: ChapterProgressOut | None = None


NoteSource = Literal["keyboard", "photo", "mixed"]


class NotesIn(BaseModel):
    raw_text: str = Field(max_length=200_000)
    source: NoteSource | None = None
    # « photo » : garde une version des notes juste après l'import d'une photo.
    checkpoint: Literal["photo"] | None = None


NoteVersionReason = Literal["auto", "photo", "structure", "before_restore", "big_deletion"]


class NoteVersionOut(BaseModel):
    id: int
    reason: NoteVersionReason
    source: str
    created_at: UTCDatetime
    words: int
    preview: str


class NoteVersionContentOut(NoteVersionOut):
    raw_text: str


class TrashItemOut(BaseModel):
    id: int
    title: str
    subject: SubjectOut
    deleted_at: UTCDatetime
    expires_at: UTCDatetime


class NotesOut(ORMModel):
    chapter_id: int
    raw_text: str
    source: str
    updated_at: UTCDatetime


class CourseOut(BaseModel):
    chapter_id: int
    content_markdown: str
    version: int
    origin: str
    created_at: UTCDatetime
    notes_changed: bool
    has_manual_changes: bool
    title: str


class CourseIn(BaseModel):
    content_markdown: str = Field(max_length=500_000)


class CourseVersionOut(ORMModel):
    version: int
    origin: str
    created_at: UTCDatetime


class CourseVersionContentOut(CourseVersionOut):
    content_markdown: str


class SuggestionOut(ORMModel):
    id: int
    chapter_id: int
    type: str
    original_text: str
    suggested_text: str
    reason: str
    confidence: float
    status: str
    source_reference: str
    created_at: UTCDatetime
    decided_at: UTCDatetime | None


class AcceptIn(BaseModel):
    occurrence: int | None = None


class AcceptOut(BaseModel):
    suggestion: SuggestionOut
    course: CourseOut


class ImageOut(BaseModel):
    url: str


class UncertainSpotOut(BaseModel):
    guess: str
    options: list[str]


class FigureOut(BaseModel):
    """Un schéma découpé sur la photo : `index` = rang du « [schéma : …] » dans le texte lu."""

    index: int
    url: str


class PhotoOut(BaseModel):
    """Texte lu ; chaque [?] correspond, dans l'ordre, à un élément de « uncertain »."""

    text: str
    uncertain: list[UncertainSpotOut]
    url: str  # la photo d'origine, conservée avec le chapitre
    figures: list[FigureOut] = []  # schémas découpés automatiquement


class StoredPhotoOut(BaseModel):
    url: str
    created_at: UTCDatetime


class ReferenceDocumentOut(ORMModel):
    id: int
    subject_id: int
    title: str
    source: str
    url: str
    school_year: str
    file_path: str
    chunk_count: int
    updated_at: UTCDatetime


class ReferenceDocumentContentOut(ReferenceDocumentOut):
    content: str


class SyncReportOut(BaseModel):
    added: int
    updated: int
    removed: int
    unchanged: int
    errors: list[str]


class RevisionSheetOut(BaseModel):
    chapter_id: int
    content_markdown: str
    course_version: int
    outdated: bool
    created_at: UTCDatetime


class QuizQuestionOut(BaseModel):
    type: str
    question: str
    choices: list[str]
    answer: str
    explanation: str
    course_excerpt: str


class QuizOut(BaseModel):
    chapter_id: int
    questions: list[QuizQuestionOut]
    course_version: int
    outdated: bool
    created_at: UTCDatetime


class ExplainIn(BaseModel):
    passage: str = Field(min_length=1, max_length=2000)
    mode: Literal["simpler", "example", "question"]


class ExplainOut(BaseModel):
    text: str
    answer: str


class ChatGPTStatusOut(BaseModel):
    ai_provider: str
    connected: bool
    email: str
    name: str
    model: str
    needs_reauth: bool
    redirect_uri: str


class ChatGPTLoginOut(BaseModel):
    authorization_url: str


class ChatGPTModelOut(BaseModel):
    slug: str
    display_name: str


class ChatGPTModelIn(BaseModel):
    model: str = Field(min_length=1, max_length=200)


class ChatGPTLogoutOut(BaseModel):
    revoked: bool


class SearchResultOut(BaseModel):
    chapter_id: int
    title: str
    subject: str
    snippet: str


class OperationUsageOut(BaseModel):
    operation: str
    calls: int
    errors: int
    input_tokens: int
    output_tokens: int
    cost_eur: float


class RecentRunOut(BaseModel):
    created_at: UTCDatetime
    operation: str
    chapter_title: str
    provider: str
    model: str
    status: str
    error_code: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


class UsageDetailsOut(BaseModel):
    ai_provider: str
    last_7_days: list[OperationUsageOut]
    this_month: list[OperationUsageOut]
    recent: list[RecentRunOut]
    chatgpt_usage_url: str


class UsageOut(BaseModel):
    month_cost_eur: float
    budget_eur: float
    cost_tracking: bool


class LoginIn(BaseModel):
    password: str


class AuthStatus(BaseModel):
    auth_required: bool
    authenticated: bool


class AIConfigIn(BaseModel):
    ai_provider: Literal["openai", "chatgpt", "local", "fake"]
    openai_api_key: str = Field(default="", max_length=300)
    local_ai_base_url: str = Field(default="", max_length=300)
    local_ai_model: str = Field(default="", max_length=100)


class SetupStatusOut(BaseModel):
    needs_setup: bool
    ai_provider: str
    has_openai_key: bool
    local_ai_base_url: str
    local_ai_model: str
    chatgpt_connected: bool


class TestResultOut(BaseModel):
    ok: bool
    message: str


class StudentSubjectsIn(BaseModel):
    subject_ids: list[int] = Field(max_length=100)


class DownloadReportOut(BaseModel):
    downloaded: int
    already: int
    errors: list[str]


class RedrawIn(BaseModel):
    url: str = Field(max_length=300)  # l'image photographiée du chapitre
    # Pour corriger une première version : son adresse (.svg) et ce qui ne va pas.
    previous_url: str = Field(default="", max_length=300)
    remark: str = Field(default="", max_length=500)
    hand: bool = False  # aspect manuscrit (police et traits)


class RestyleIn(BaseModel):
    url: str = Field(max_length=300)  # un schéma redessiné (.svg)
    hand: bool


class RedrawOut(BaseModel):
    url: str
    corrections: list[str] = []  # erreurs corrigées ou doutes, expliqués à l'élève
