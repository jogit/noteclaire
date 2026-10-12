from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Student(Base):
    """Un élève : ses chapitres sont séparés de ceux des autres élèves de la famille."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    level: Mapped[str] = mapped_column(String(30), default="seconde")
    # Particularités à respecter dans les explications et fiches : identifiants de la liste
    # (levels.ADAPTATIONS) séparés par des virgules, plus un texte libre facultatif.
    adaptation_codes: Mapped[str] = mapped_column(String(300), default="")
    adaptation_notes: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class StudentSubject(Base):
    """Matière activée pour un élève (les matières elles-mêmes sont communes)."""

    __tablename__ = "student_subjects"

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), primary_key=True)


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    school_year: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    # Corbeille : un chapitre supprimé est gardé 30 jours avant d'être effacé.
    deleted_at: Mapped[datetime | None] = mapped_column(index=True)

    subject: Mapped[Subject] = relationship()
    student: Mapped[Student] = relationship()
    note: Mapped["Note"] = relationship(
        back_populates="chapter", cascade="all, delete-orphan", uselist=False
    )


class Note(Base):
    """Notes originales de l'élève. Jamais modifiées par l'IA."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), unique=True
    )
    raw_text: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(20), default="keyboard")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    chapter: Mapped[Chapter] = relationship(back_populates="note")


class AIRun(Base):
    """Journal d'un appel IA. Ne contient jamais le contenu complet du cours."""

    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int | None] = mapped_column(
        ForeignKey("chapters.id", ondelete="SET NULL"), index=True
    )
    operation: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(20))
    input_hash: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    estimated_cost_eur: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(50))
    duration_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Course(Base):
    """Une version du cours. Une version n'est jamais modifiée ni supprimée."""

    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint("chapter_id", "version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    content_markdown: Mapped[str] = mapped_column(Text)
    version: Mapped[int]
    origin: Mapped[str] = mapped_column(String(30))
    source_notes_hash: Mapped[str] = mapped_column(String(64))
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AISuggestion(Base):
    """Proposition de l'IA. N'est appliquée au cours que sur décision de l'utilisateur."""

    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    course_version_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(30))
    original_text: Mapped[str] = mapped_column(Text)
    suggested_text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    status: Mapped[str] = mapped_column(String(20), default="pending")
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    # Titre du document de référence sur lequel s'appuie la suggestion (vérifié), ou vide.
    source_reference: Mapped[str] = mapped_column(String(300), default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    decided_at: Mapped[datetime | None]


class ReferenceDocument(Base):
    """Document pédagogique de référence (programme officiel, manuel…), découpé en extraits."""

    __tablename__ = "reference_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    source: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(1000), default="")
    level: Mapped[str] = mapped_column(String(30), default="seconde")
    school_year: Mapped[str] = mapped_column(String(20), default="")
    # Chemin relatif au dossier des références : le fichier est la source de vérité.
    file_path: Mapped[str] = mapped_column(String(500), unique=True)
    file_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    subject: Mapped[Subject] = relationship()
    chunks: Mapped[list["ReferenceChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="ReferenceChunk.position"
    )


class ReferenceChunk(Base):
    """Extrait d'un document de référence, indexé en plein texte (table FTS5)."""

    __tablename__ = "reference_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("reference_documents.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int]
    heading: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text)

    document: Mapped[ReferenceDocument] = relationship(back_populates="chunks")


class RevisionSheet(Base):
    """Fiche de révision générée depuis une version du cours."""

    __tablename__ = "revision_sheets"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    course_version_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    content_markdown: Mapped[str] = mapped_column(Text)
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Quiz(Base):
    """Quiz généré depuis une version du cours. Questions stockées en JSON."""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    course_version_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    questions_json: Mapped[str] = mapped_column(Text)
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_runs.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class NoteVersion(Base):
    """Version des notes (photo importée, avant mise au propre, saisie…). Jamais modifiée."""

    __tablename__ = "note_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    chapter_id: Mapped[int] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), index=True
    )
    raw_text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
