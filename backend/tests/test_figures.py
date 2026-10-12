import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.services.ai.base import (
    AIProviderError,
    AIResponse,
    FigureBox,
    FigureLocations,
    FiguresRequest,
    PhotoResult,
    RedrawRequest,
    RedrawResult,
    SchemaArrow,
    SchemaText,
)
from app.services.ai.fake_provider import FakeProvider
from app.services.figure_service import describe_schemas
from tests.test_photo import photo, upload

TEXT = "début\n[schéma : flèches annotées]\nmilieu\n[schéma : un cycle]\nfin"


def scene(
    text: str = "ok", head_start: bool = False, corrections: list[str] | None = None
) -> RedrawResult:
    return RedrawResult(
        inventory=["une flèche"],
        texts=[SchemaText(x=5, y=20, text=text, size=24, color="bleu")],
        arrows=[
            SchemaArrow(d="M 10 50 L 90 50", head_start=head_start, head_end=True, color="vert")
        ],
        lines=[],
        corrections=corrections or [],
    )


def read(provider: FakeProvider, text: str) -> None:
    provider.responses.append(AIResponse(PhotoResult(text=text, uncertain=[]), 0, 0))


def boxes(*values: tuple[int, int, int, int]) -> AIResponse[FigureLocations]:
    items = [FigureBox(x_min=a, y_min=b, x_max=c, y_max=d) for a, b, c, d in values]
    return AIResponse(FigureLocations(boxes=items), 0, 0)


def test_schemas_are_cropped_and_stored_with_the_chapter(
    client: TestClient, settings: Settings, fake_provider: FakeProvider, chapter_id: int
) -> None:
    read(fake_provider, TEXT)
    fake_provider.responses.append(boxes((100, 100, 500, 400), (500, 500, 900, 900)))

    response = upload(client, chapter_id, photo(1000, 800))

    figures = response.json()["figures"]
    assert [f["index"] for f in figures] == [0, 1]
    names = [f["url"].rsplit("/", 1)[1] for f in figures]
    stored = settings.data_dir / "images" / str(chapter_id)
    first = Image.open(stored / names[0])
    assert first.format == "JPEG"
    assert 400 <= first.size[0] <= 480 and 240 <= first.size[1] <= 300  # rectangle + contour
    request = fake_provider.requests[-1]
    assert isinstance(request, FiguresRequest)
    assert request.descriptions == ("flèches annotées", "un cycle")
    assert client.get(figures[0]["url"]).status_code == 200


def test_no_schema_means_no_extra_ai_call(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    read(fake_provider, "juste du texte")
    assert upload(client, chapter_id, photo(800, 600)).json()["figures"] == []
    assert not any(isinstance(r, FiguresRequest) for r in fake_provider.requests)


def test_a_failed_figure_lookup_keeps_the_text(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    read(fake_provider, TEXT)
    fake_provider.responses.append(AIProviderError("ai_unavailable"))
    response = upload(client, chapter_id, photo(800, 600))
    assert response.status_code == 200
    assert response.json()["text"] == TEXT
    assert response.json()["figures"] == []


def test_unusable_rectangles_are_skipped(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    read(fake_provider, TEXT)
    fake_provider.responses.append(boxes((100, 100, 110, 400), (500, 500, 900, 900), (0, 0, 5, 5)))
    figures = upload(client, chapter_id, photo(800, 600)).json()["figures"]
    assert [f["index"] for f in figures] == [1]  # trop fin, valide, et un troisième en trop


def stored_image(client: TestClient, chapter_id: int) -> str:
    read(client.app.state.ai_provider, "[schéma : un cycle]")  # type: ignore[attr-defined]
    figures = upload(client, chapter_id, photo(800, 600)).json()["figures"]
    return str(figures[0]["url"])


def test_redraw_stores_a_clean_svg_next_to_the_photo(
    client: TestClient, settings: Settings, fake_provider: FakeProvider, chapter_id: int
) -> None:
    client.put(f"/api/chapters/{chapter_id}/notes", json={"raw_text": "sens de réaction"})
    url = stored_image(client, chapter_id)
    fake_provider.responses.append(AIResponse(scene(), 0, 0))

    response = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url})

    assert response.status_code == 200
    svg_url = response.json()["url"]
    assert svg_url.endswith(".svg") and svg_url != url
    request = fake_provider.requests[-1]
    assert isinstance(request, RedrawRequest)
    assert "sens de réaction" in request.context  # les notes aident à lire l'écriture
    assert (settings.data_dir / "images").exists()
    served = client.get(svg_url)
    assert served.headers["content-type"] == "image/svg+xml"
    assert "sandbox" in served.headers["content-security-policy"]
    assert served.headers["x-content-type-options"] == "nosniff"
    assert client.get(url).headers["content-type"] == "image/jpeg"  # l'original est intact


def test_redraw_never_writes_what_the_ai_says_as_markup(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    fake_provider.responses.append(AIResponse(scene("</text><script>alert(1)</script>"), 0, 0))
    svg_url = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url}).json()[
        "url"
    ]
    body = client.get(svg_url).text
    assert "<script" not in body and "&lt;script&gt;" in body


def test_redraw_refuses_unusable_or_foreign_images(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    broken = RedrawResult(inventory=[], texts=[], arrows=[], lines=[], corrections=[])
    fake_provider.responses.append(AIResponse(broken, 0, 0))
    bad = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url})
    assert bad.status_code == 502 and bad.json()["error"]["code"] == "schema_invalid"

    for other in (
        "/api/images/999/" + "a" * 32 + ".jpg",
        "../../etc/passwd",
        url.replace(".jpg", ".svg"),
    ):
        response = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": other})
        assert response.status_code == 404


def test_cropped_files_are_jpeg_images_of_the_chapter(
    client: TestClient, settings: Settings, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    name = url.rsplit("/", 1)[1]
    data = Path(settings.data_dir / "images" / str(chapter_id) / name).read_bytes()
    assert Image.open(io.BytesIO(data)).format == "JPEG"


def test_redraw_can_be_corrected_with_a_remark_on_the_first_version(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    fake_provider.responses.append(AIResponse(scene(), 0, 0))
    first = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url}).json()[
        "url"
    ]

    fixed = client.post(
        f"/api/chapters/{chapter_id}/schemas/redraw",
        json={"url": url, "previous_url": first, "remark": "  il manque la pointe à gauche  "},
    )

    assert fixed.status_code == 200 and fixed.json()["url"] not in (url, first)
    request = fake_provider.requests[-1]
    assert isinstance(request, RedrawRequest)
    assert request.remark == "il manque la pointe à gauche"
    assert "head_end" in request.previous_scene  # la première version est renvoyée à l'IA


def test_a_remark_needs_a_first_version_of_this_chapter(
    client: TestClient, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    for previous in ("", url, "/api/images/999/" + "a" * 32 + ".svg"):
        response = client.post(
            f"/api/chapters/{chapter_id}/schemas/redraw",
            json={"url": url, "previous_url": previous, "remark": "corrige"},
        )
        assert response.status_code == 404


def test_restyle_gives_the_same_schema_with_a_hand_look_without_calling_the_ai(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    fake_provider.responses.append(AIResponse(scene(), 0, 0))
    clean = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url}).json()[
        "url"
    ]
    calls = len(fake_provider.requests)

    hand = client.post(
        f"/api/chapters/{chapter_id}/schemas/restyle", json={"url": clean, "hand": True}
    )

    assert hand.status_code == 200 and hand.json()["url"] != clean
    assert "Caveat" in client.get(hand.json()["url"]).text
    assert len(fake_provider.requests) == calls
    for bad in (url, "/api/images/999/" + "a" * 32 + ".svg"):
        refused = client.post(
            f"/api/chapters/{chapter_id}/schemas/restyle", json={"url": bad, "hand": True}
        )
        assert refused.status_code == 404


def test_redraw_reports_the_errors_the_ai_corrected(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    explanation = "Tu avais écrit ⇉ ; j'ai mis ⇌ : la réaction est un équilibre."
    fake_provider.responses.append(AIResponse(scene(corrections=[explanation]), 0, 0))

    body = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url}).json()

    assert body["corrections"] == [explanation]


def test_the_ai_reads_a_redrawn_schema_as_text_not_as_a_url(
    client: TestClient, settings: Settings, fake_provider: FakeProvider, chapter_id: int
) -> None:
    url = stored_image(client, chapter_id)
    fake_provider.responses.append(AIResponse(scene(text="état"), 0, 0))
    clean = client.post(f"/api/chapters/{chapter_id}/schemas/redraw", json={"url": url}).json()[
        "url"
    ]

    described = describe_schemas(settings, f"avant\n![mon schéma]({clean})\n![photo]({url})\naprès")

    assert "état" in described and "une flèche" in described and clean not in described
    assert f"![photo]({url})" in described  # une photo non redessinée reste telle quelle
    unknown = "![x](/api/images/999/" + "a" * 32 + ".svg)"
    assert describe_schemas(settings, unknown) == "[schéma : x]"
