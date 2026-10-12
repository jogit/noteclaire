import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import Settings
from app.models import ReferenceDocument
from app.services import reference_search, reference_service
from app.services.ai.base import AIResponse, AnalyzeRequest, AnalyzeResult, SuggestionItem
from app.services.ai.fake_provider import FakeProvider
from app.services.reference_search import build_query
from app.services.reference_service import references_root, split_chunks
from tests.conftest import structured

PROGRAMME = """---
title: Programme de mathématiques de seconde
source: Bulletin officiel
url: https://example.org/programme.pdf
---

# Fonctions

## Fonctions affines

Une fonction affine est définie par f(x) = ax + b. Le coefficient directeur a
donne le sens de variation. Une fonction linéaire est une fonction affine telle que b = 0.

## Fonctions de référence

Fonction carré, fonction inverse, fonction racine carrée, fonction valeur absolue.

# Probabilités

Probabilités conditionnelles et arbres pondérés.
"""


def minimal_pdf(text: str) -> bytes:
    """PDF d'une page contenant `text`, écrit à la main (aucune dépendance)."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return out


def write(settings: Settings, relative: str, content: str | bytes) -> Path:
    path = references_root(settings) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def sync(client: TestClient) -> dict[str, Any]:
    report: dict[str, Any] = client.post("/api/references/sync").json()
    return report


def test_split_chunks_keeps_headings_and_size() -> None:
    chunks = split_chunks(PROGRAMME.split("---", 2)[2])
    assert [h for h, _ in chunks] == ["Fonctions affines", "Fonctions de référence", "Probabilités"]
    long_chunks = split_chunks("Une phrase assez longue. " * 200, max_chars=300)
    assert all(len(body) <= 300 for _, body in long_chunks)
    assert len(long_chunks) > 10


def test_build_query_ignores_stopwords_and_accents() -> None:
    query = build_query("Les fonctions affines : la fonction affine définie dans le cours")
    assert query.startswith('"fonctions" OR "affines"') or '"affine"' in query
    assert '"definie"' in query
    assert "dans" not in query
    assert build_query("a b c") == ""


def test_sync_indexes_markdown_text_and_pdf(client: TestClient, settings: Settings) -> None:
    write(settings, "seconde/mathematiques/programme.md", PROGRAMME)
    write(
        settings,
        "seconde/svt/la-cellule.txt",
        "La cellule est l'unite du vivant.\n\nMembrane, noyau.",
    )
    write(settings, "seconde/physique-chimie/mouvement.pdf", minimal_pdf("Le mouvement rectiligne"))
    write(settings, "seconde/inconnue/doc.md", "texte")
    write(settings, "seconde/mathematiques/image.png", b"\x89PNG")

    report = sync(client)

    assert (report["added"], report["removed"]) == (3, 0)
    assert report["errors"] == ["seconde/inconnue/doc.md : matière inconnue"]
    documents = {d["file_path"]: d for d in client.get("/api/references").json()}
    maths = documents["seconde/mathematiques/programme.md"]
    assert maths["title"] == "Programme de mathématiques de seconde"
    assert maths["source"] == "Bulletin officiel"
    assert maths["chunk_count"] == 3
    assert documents["seconde/svt/la-cellule.txt"]["title"] == "La cellule"
    pdf = client.get(f"/api/references/{documents['seconde/physique-chimie/mouvement.pdf']['id']}")
    assert "mouvement rectiligne" in pdf.json()["content"]


def test_sync_is_idempotent_and_follows_files(client: TestClient, settings: Settings) -> None:
    path = write(settings, "seconde/mathematiques/programme.md", PROGRAMME)
    sync(client)
    assert sync(client)["unchanged"] == 1

    path.write_text(PROGRAMME.replace("Probabilités conditionnelles", "Statistiques"), "utf-8")
    assert sync(client)["updated"] == 1

    sidecar = path.with_name(path.name + ".meta.json")
    sidecar.write_text(json.dumps({"title": "Titre du fichier voisin"}), "utf-8")
    sync(client)
    [document] = client.get("/api/references").json()
    # L'en-tête du Markdown n'écrase pas le fichier voisin.
    assert document["title"] == "Titre du fichier voisin"

    path.unlink()
    assert sync(client)["removed"] == 1
    assert client.get("/api/references").json() == []


def test_references_are_indexed_at_startup(app: FastAPI, settings: Settings) -> None:
    write(settings, "seconde/svt/cellule.md", "# La cellule\n\nUnité du vivant.")
    with TestClient(app) as client:
        assert len(client.get("/api/references").json()) == 1


def test_search_ranks_by_relevance_and_filters_subject(
    client: TestClient, app: FastAPI, settings: Settings
) -> None:
    write(settings, "seconde/mathematiques/programme.md", PROGRAMME)
    write(
        settings,
        "seconde/svt/fonctions.md",
        "# Fonctions\n\nLes fonctions du rein : fonction affine.",
    )
    sync(client)
    maths_id = client.get("/api/subjects").json()[1]["id"]

    with app.state.db.session_factory() as db:
        excerpts = reference_search.search_references(
            db,
            maths_id,
            "seconde",
            "fonction affine, coefficient directeur et ordonnee a l'origine",
        )

    assert excerpts[0].heading == "Fonctions affines"
    assert {e.document_title for e in excerpts} == {"Programme de mathématiques de seconde"}
    context = reference_search.format_context(excerpts)
    assert 'Document : "Programme de mathématiques de seconde"' in context
    assert "(source : Bulletin officiel)" in context


def test_upload_and_delete(client: TestClient, settings: Settings) -> None:
    subject_id = client.get("/api/subjects").json()[5]["id"]  # SVT
    response = client.post(
        "/api/references",
        data={"subject_id": str(subject_id), "title": "Ma fiche", "source": "Manuel"},
        files={"file": ("La Cellule (cours).md", b"# Cellule\n\nNoyau.", "text/markdown")},
    )

    assert response.status_code == 201, response.text
    document = response.json()
    assert (document["title"], document["source"]) == ("Ma fiche", "Manuel")
    assert document["file_path"] == "seconde/svt/la-cellule-cours.md"
    stored = references_root(settings) / document["file_path"]
    assert stored.exists()

    same_name = client.post(
        "/api/references",
        data={"subject_id": str(subject_id)},
        files={"file": ("La Cellule (cours).md", b"# Autre\n\nTexte.", "text/markdown")},
    ).json()
    assert same_name["file_path"] == "seconde/svt/la-cellule-cours-2.md"

    assert client.delete(f"/api/references/{document['id']}").status_code == 204
    assert not stored.exists()
    assert not stored.with_name(stored.name + ".meta.json").exists()
    assert len(client.get("/api/references").json()) == 1


@pytest.mark.parametrize(
    ("filename", "content", "code"),
    [
        ("image.png", b"\x89PNG", "reference_unsupported"),
        ("vide.md", b"", "reference_empty"),
        ("casse.pdf", b"pas un pdf", "reference_unreadable"),
    ],
)
def test_upload_errors(
    client: TestClient, settings: Settings, filename: str, content: bytes, code: str
) -> None:
    subject_id = client.get("/api/subjects").json()[0]["id"]
    response = client.post(
        "/api/references",
        data={"subject_id": str(subject_id)},
        files={"file": (filename, content, "application/octet-stream")},
    )
    assert response.json()["error"]["code"] == code
    folder = references_root(settings) / "seconde" / "francais"
    assert not folder.exists() or list(folder.iterdir()) == []


def test_analysis_uses_references_and_checks_cited_source(
    client: TestClient, fake_provider: FakeProvider, settings: Settings, chapter_id: int
) -> None:
    write(settings, "seconde/mathematiques/programme.md", PROGRAMME)
    sync(client)
    structured(client, chapter_id, "notes", "# Fonctions affines\n\nf(x) = ax + b\n")

    def item(reference: str) -> SuggestionItem:
        return SuggestionItem(
            type="addition",
            original_text="f(x) = ax + b",
            suggested_text="Si b = 0, la fonction est linéaire.",
            reason="Le programme le mentionne.",
            confidence=0.8,
            reference_title=reference,
        )

    fake_provider.responses.append(
        AIResponse(
            AnalyzeResult(
                suggestions=[item("Programme de mathématiques de seconde"), item("Inventé")]
            )
        )
    )
    suggestions = client.post(f"/api/chapters/{chapter_id}/analyze").json()

    request = fake_provider.requests[-1]
    assert isinstance(request, AnalyzeRequest)
    assert "Une fonction linéaire est une fonction affine" in request.reference_context
    assert request.reference_titles == ("Programme de mathématiques de seconde",)
    assert [s["source_reference"] for s in suggestions] == [
        "Programme de mathématiques de seconde",
        "",
    ]


def test_analysis_without_references(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    structured(client, chapter_id, "notes", "# Cours\n\ntexte\n")
    client.post(f"/api/chapters/{chapter_id}/analyze")
    request = fake_provider.requests[-1]
    assert isinstance(request, AnalyzeRequest)
    assert "Aucun document de référence" in request.reference_context


def test_references_follow_the_student_level(client: TestClient, settings: Settings) -> None:
    write(settings, "seconde/mathematiques/programme.md", PROGRAMME)
    write(settings, "premiere/mathematiques/suites.md", "# Suites\n\nUne suite arithmétique.")
    write(settings, "quatrieme/mathematiques/autre.md", "texte")
    report = sync(client)
    assert report["added"] == 2
    assert report["errors"] == ["quatrieme/mathematiques/autre.md : classe inconnue"]

    assert [d["file_path"] for d in client.get("/api/references").json()] == [
        "seconde/mathematiques/programme.md"
    ]
    premiere = client.post("/api/students", json={"name": "Léa", "level": "premiere"}).json()
    documents = client.get("/api/references", headers={"X-Student-Id": str(premiere["id"])})
    assert [d["file_path"] for d in documents.json()] == ["premiere/mathematiques/suites.md"]


def test_unreadable_file_does_not_block_others(client: TestClient, settings: Settings) -> None:
    folder = settings.data_dir / "references" / "seconde" / "francais"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "a-bon.md").write_text("# Titre\n\nUn texte valide sur les fonctions affines.")
    (folder / "z-casse.pdf").write_bytes(b"pas un pdf")
    with client.app.state.db.session_factory() as db:  # type: ignore[attr-defined]
        report = reference_service.sync_references(db, settings)
        paths = [d.file_path for d in db.scalars(select(ReferenceDocument))]
    assert report.added == 1
    assert len(report.errors) == 1
    assert paths == ["seconde/francais/a-bon.md"]
