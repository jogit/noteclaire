"""schema initial

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("adaptation_codes", sa.String(length=300), nullable=False),
        sa.Column("adaptation_notes", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "student_subjects",
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
        sa.PrimaryKeyConstraint("student_id", "subject_id"),
    )
    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("school_year", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["students.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("chapters", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_chapters_subject_id"), ["subject_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_chapters_student_id"), ["student_id"], unique=False)

    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=20), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_eur", sa.Double(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_runs", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ai_runs_chapter_id"), ["chapter_id"], unique=False)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id"),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("origin", sa.String(length=30), nullable=False),
        sa.Column("source_notes_hash", sa.String(length=64), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chapter_id", "version"),
    )
    with op.batch_alter_table("courses", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_courses_chapter_id"), ["chapter_id"], unique=False)

    # ### end Alembic commands ###

    op.create_table(
        "ai_suggestions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("course_version_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Double(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_version_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_ai_suggestions_chapter_id"), ["chapter_id"], unique=False
        )

    # ### end Alembic commands ###

    op.create_table(
        "reference_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("source", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("school_year", sa.String(length=20), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_path"),
    )
    with op.batch_alter_table("reference_documents", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reference_documents_subject_id"), ["subject_id"], unique=False
        )

    op.create_table(
        "reference_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(length=300), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["reference_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("reference_chunks", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reference_chunks_document_id"), ["document_id"], unique=False
        )

    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("source_reference", sa.String(length=300), server_default="", nullable=False)
        )

    # Index plein texte des extraits (SPEC §20 : SQLite FTS5, sans base vectorielle).
    # remove_diacritics : « équation » est trouvé en cherchant « equation ».
    op.execute(
        """
        CREATE VIRTUAL TABLE reference_chunks_fts USING fts5(
            heading, content,
            content='reference_chunks', content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )
    op.execute(
        """
        CREATE TRIGGER reference_chunks_ai AFTER INSERT ON reference_chunks BEGIN
            INSERT INTO reference_chunks_fts(rowid, heading, content)
            VALUES (new.id, new.heading, new.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER reference_chunks_ad AFTER DELETE ON reference_chunks BEGIN
            INSERT INTO reference_chunks_fts(reference_chunks_fts, rowid, heading, content)
            VALUES ('delete', old.id, old.heading, old.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER reference_chunks_au AFTER UPDATE ON reference_chunks BEGIN
            INSERT INTO reference_chunks_fts(reference_chunks_fts, rowid, heading, content)
            VALUES ('delete', old.id, old.heading, old.content);
            INSERT INTO reference_chunks_fts(rowid, heading, content)
            VALUES (new.id, new.heading, new.content);
        END
        """
    )
    # ### end Alembic commands ###

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("course_version_id", sa.Integer(), nullable=False),
        sa.Column("questions_json", sa.Text(), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_version_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("quizzes", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_quizzes_chapter_id"), ["chapter_id"], unique=False)

    op.create_table(
        "revision_sheets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("course_version_id", sa.Integer(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("ai_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_version_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("revision_sheets", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_revision_sheets_chapter_id"), ["chapter_id"], unique=False
        )

    # Recherche dans les chapitres (SPEC §23) : table FTS5 autonome, tenue à jour par
    # search_service.index_chapter (titre, matière, notes et cours courant).
    op.execute(
        """
        CREATE VIRTUAL TABLE chapter_search_fts USING fts5(
            chapter_id UNINDEXED, title, subject, notes, course,
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )
    # ### end Alembic commands ###

    op.create_table(
        "note_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("note_versions", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_note_versions_chapter_id"), ["chapter_id"], unique=False
        )

    with op.batch_alter_table("chapters", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f("ix_chapters_deleted_at"), ["deleted_at"], unique=False)

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("chapters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chapters_deleted_at"))
        batch_op.drop_column("deleted_at")

    with op.batch_alter_table("note_versions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_note_versions_chapter_id"))

    op.drop_table("note_versions")
    # ### end Alembic commands ###

    op.execute("DROP TABLE IF EXISTS chapter_search_fts")
    with op.batch_alter_table("revision_sheets", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_revision_sheets_chapter_id"))

    op.drop_table("revision_sheets")
    with op.batch_alter_table("quizzes", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_quizzes_chapter_id"))

    op.drop_table("quizzes")
    # ### end Alembic commands ###

    for trigger in ("reference_chunks_ai", "reference_chunks_ad", "reference_chunks_au"):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger}")
    op.execute("DROP TABLE IF EXISTS reference_chunks_fts")
    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.drop_column("source_reference")

    with op.batch_alter_table("reference_chunks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reference_chunks_document_id"))

    op.drop_table("reference_chunks")
    with op.batch_alter_table("reference_documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reference_documents_subject_id"))

    op.drop_table("reference_documents")
    # ### end Alembic commands ###

    with op.batch_alter_table("ai_suggestions", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ai_suggestions_chapter_id"))

    op.drop_table("ai_suggestions")
    # ### end Alembic commands ###

    with op.batch_alter_table("courses", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_courses_chapter_id"))

    op.drop_table("courses")
    op.drop_table("notes")
    with op.batch_alter_table("ai_runs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ai_runs_chapter_id"))

    op.drop_table("ai_runs")
    with op.batch_alter_table("chapters", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_chapters_student_id"))
        batch_op.drop_index(batch_op.f("ix_chapters_subject_id"))

    op.drop_table("chapters")
    op.drop_table("student_subjects")
    op.drop_table("students")
    op.drop_table("subjects")
    # ### end Alembic commands ###
