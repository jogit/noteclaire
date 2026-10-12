import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.levels import LEVEL_IDS
from app.services import reference_catalog
from app.services.reference_service import references_root
from app.subjects import SUBJECTS
from tests.test_references import minimal_pdf

SECONDE = reference_catalog.catalog_entries("seconde")


def serve(monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport) -> None:
    monkeypatch.setattr(
        reference_catalog, "_client", lambda: httpx.Client(transport=handler, follow_redirects=True)
    )


def test_catalog_covers_every_core_seconde_subject() -> None:
    core = {
        "francais", "mathematiques", "histoire-geographie", "ses", "physique-chimie",
        "svt", "anglais", "espagnol", "allemand", "snt", "emc",
    }  # fmt: skip
    assert core <= {e["subject"] for e in SECONDE}
    assert all(e["url"].startswith("https://") and e["title"] for e in SECONDE)


def test_download_indexes_programmes_once_per_url(
    client: TestClient, settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(str(request.url))
        return httpx.Response(200, content=minimal_pdf("Programme officiel de la matière"))

    serve(monkeypatch, httpx.MockTransport(handler))

    report = client.post("/api/references/download").json()
    assert (report["downloaded"], report["already"], report["errors"]) == (len(SECONDE), 0, [])
    assert len(requested) == len(
        {e["url"] for e in SECONDE}
    )  # les langues vivantes partagent un PDF
    documents = client.get("/api/references").json()
    assert len(documents) == len(SECONDE)
    assert all(d["source"] for d in documents)
    assert (references_root(settings) / "seconde" / "francais").is_dir()

    again = client.post("/api/references/download").json()
    assert (again["downloaded"], again["already"]) == (0, len(SECONDE))
    assert len(requested) == len({e["url"] for e in SECONDE})


def test_download_reports_failures_and_keeps_going(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = SECONDE[0]["url"]
    html = SECONDE[1]["url"]

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == broken:
            return httpx.Response(404)
        if str(request.url) == html:
            return httpx.Response(200, content=b"<html>pas un pdf</html>")
        return httpx.Response(200, content=minimal_pdf("Texte du programme"))

    serve(monkeypatch, httpx.MockTransport(handler))

    report = client.post("/api/references/download").json()
    assert len(report["errors"]) == 2
    assert report["downloaded"] == len(SECONDE) - 2
    assert len(client.get("/api/references").json()) == len(SECONDE) - 2


def test_every_catalog_entry_targets_a_known_level_and_subject() -> None:
    slugs = {slug for slug, _ in SUBJECTS}
    for level in LEVEL_IDS:
        for entry in reference_catalog.catalog_entries(level):
            assert entry["subject"] in slugs, entry["title"]
    assert sum(len(reference_catalog.catalog_entries(level)) for level in LEVEL_IDS) == len(
        reference_catalog.catalog_entries_all()
    )
