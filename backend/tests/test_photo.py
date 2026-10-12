import base64
import io
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from app.services.ai.base import AIResponse, PhotoRequest, PhotoResult, UncertainSpot
from app.services.ai.fake_provider import FakeProvider
from app.services.ai.openai_provider import responses_input
from app.services.photo_service import MAX_SIDE, prepare_image

GPS_TAG = 0x8825
ORIENTATION_TAG = 0x0112


def photo(width: int = 3000, height: int = 1000, orientation: int = 1) -> bytes:
    """JPEG avec position GPS et orientation dans les métadonnées, comme un téléphone."""
    image = Image.new("RGB", (width, height), "white")
    exif = Image.Exif()
    exif[ORIENTATION_TAG] = orientation
    exif[GPS_TAG] = {1: "N", 2: (48.0, 51.0, 24.0)}
    output = io.BytesIO()
    image.save(output, format="JPEG", exif=exif)
    return output.getvalue()


def test_prepare_image_strips_metadata_rotates_and_resizes() -> None:
    prepared = Image.open(io.BytesIO(prepare_image(photo(orientation=6))))
    # Orientation 6 = photo prise en portrait : l'image est redressée (largeur ↔ hauteur).
    assert prepared.size == (683, MAX_SIDE)
    assert prepared.format == "JPEG"
    exif = prepared.getexif()
    assert GPS_TAG not in exif and ORIENTATION_TAG not in exif


def upload(client: TestClient, chapter_id: int, data: bytes, kind: str = "image/jpeg") -> Any:
    return client.post(
        f"/api/chapters/{chapter_id}/photo", files={"image": ("page.jpg", data, kind)}
    )


def test_photo_is_read_and_not_stored(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int, tmp_path: Any
) -> None:
    fake_provider.responses.append(AIResponse(PhotoResult(text="  vecteur AB  ", uncertain=[])))

    response = upload(client, chapter_id, photo())

    assert response.status_code == 200
    body = response.json()
    assert (body["text"], body["uncertain"]) == ("vecteur AB", [])
    assert body["url"].startswith(f"/api/photos/{chapter_id}/")
    request = fake_provider.requests[-1]
    assert isinstance(request, PhotoRequest)
    assert (request.subject, request.chapter) == ("Mathématiques", "Fonctions affines")
    assert request.image_data_url.startswith("data:image/jpeg;base64,")
    sent = Image.open(io.BytesIO(base64.b64decode(request.image_data_url.split(",", 1)[1])))
    assert GPS_TAG not in sent.getexif()
    # La photo conservée est la version sans métadonnées, relisible à tout moment.
    stored = client.get(body["url"])
    assert stored.status_code == 200 and stored.headers["content-type"] == "image/jpeg"
    assert GPS_TAG not in Image.open(io.BytesIO(stored.content)).getexif()
    listed = client.get(f"/api/chapters/{chapter_id}/photos").json()
    assert [row["url"] for row in listed] == [body["url"]]
    usage = client.get("/api/usage/details").json()["this_month"]
    assert [row["operation"] for row in usage] == ["photo"]


def test_photo_errors(client: TestClient, fake_provider: FakeProvider, chapter_id: int) -> None:
    cases = [
        (b"%PDF-1.4", "application/pdf", 415, "photo_unsupported"),
        (b"", "image/jpeg", 400, "photo_empty"),
        (b"pas une image", "image/png", 422, "photo_unreadable"),
    ]
    for data, kind, status, code in cases:
        response = upload(client, chapter_id, data, kind)
        assert (response.status_code, response.json()["error"]["code"]) == (status, code)

    fake_provider.responses.append(AIResponse(PhotoResult(text="  ", uncertain=[])))
    response = upload(client, chapter_id, photo(400, 300))
    assert response.json()["error"]["code"] == "photo_no_text"


def test_photo_unknown_chapter(client: TestClient) -> None:
    assert upload(client, 999, photo(200, 200)).status_code == 404


def test_responses_input_with_images() -> None:
    assert responses_input("lis", ("data:image/jpeg;base64,AAA",)) == [
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": "lis"},
                {
                    "type": "input_image",
                    "image_url": "data:image/jpeg;base64,AAA",
                    "detail": "high",
                },
            ],
        }
    ]


def test_uncertain_spots_are_aligned_with_markers(
    client: TestClient, fake_provider: FakeProvider, chapter_id: int
) -> None:
    fake_provider.responses.append(
        AIResponse(
            PhotoResult(
                text="la [?] est l'unité du [illisible], le [?] contient l'ADN [?]",
                uncertain=[
                    UncertainSpot(guess="cellule", options=["celule", "cellule", " "]),
                    UncertainSpot(guess="noyau", options=["noyeau", "royaume", "nayau", "x"]),
                ],
            )
        )
    )

    body = upload(client, chapter_id, photo(400, 300)).json()

    assert body["text"] == "la [?] est l'unité du [?], le [?] contient l'ADN [?]"
    assert body["uncertain"] == [
        {"guess": "cellule", "options": ["celule"]},
        {"guess": "", "options": []},  # « [illisible] » écrit par l'IA
        {"guess": "noyau", "options": ["noyeau", "royaume", "nayau"]},
        {"guess": "", "options": []},  # un [?] de trop par rapport à la liste
    ]


def test_stored_photos_are_listed_and_removed_with_the_chapter(
    client: TestClient, chapter_id: int, tmp_path: Any
) -> None:
    first = upload(client, chapter_id, photo(800, 600)).json()["url"]
    second = upload(client, chapter_id, photo(800, 600)).json()["url"]

    listed = [row["url"] for row in client.get(f"/api/chapters/{chapter_id}/photos").json()]
    assert sorted(listed) == sorted([first, second])
    assert client.get(f"/api/photos/{chapter_id}/../../app.db").status_code in {404, 422}
    assert client.get(f"/api/photos/{chapter_id}/{'0' * 32}.jpg").status_code == 404

    assert client.delete(f"/api/chapters/{chapter_id}").status_code == 204
    assert client.delete(f"/api/trash/{chapter_id}").status_code == 204
    assert client.get(first).status_code == 404
