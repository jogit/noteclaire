import io
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from tests.test_photo import GPS_TAG, photo


def test_upload_serve_and_delete_with_chapter(
    client: TestClient, settings: Settings, chapter_id: int
) -> None:
    response = client.post(
        f"/api/chapters/{chapter_id}/images",
        files={"image": ("schema.jpg", photo(3000, 2000), "image/jpeg")},
    )

    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith(f"/api/images/{chapter_id}/") and url.endswith(".jpg")
    served = client.get(url)
    assert served.headers["content-type"] == "image/jpeg"
    image = Image.open(io.BytesIO(served.content))
    assert max(image.size) == 1600
    assert GPS_TAG not in image.getexif()

    folder = Path(settings.data_dir) / "images" / str(chapter_id)
    assert len(list(folder.iterdir())) == 1
    client.delete(f"/api/chapters/{chapter_id}")
    assert folder.exists()  # gardées tant que le chapitre est dans la corbeille
    client.delete(f"/api/trash/{chapter_id}")
    assert not folder.exists()
    assert client.get(url).status_code == 404


def test_image_names_cannot_escape_the_folder(client: TestClient, chapter_id: int) -> None:
    for name in ["..%2F..%2Fapp.db", "abc.jpg", "../secrets"]:
        assert client.get(f"/api/images/{chapter_id}/{name}").status_code == 404


def test_upload_requires_chapter_and_image(client: TestClient, chapter_id: int) -> None:
    jpeg = ("a.jpg", photo(10, 10), "image/jpeg")
    assert client.post("/api/chapters/999/images", files={"image": jpeg}).status_code == 404
    pdf = ("a.pdf", b"%PDF", "application/pdf")
    assert (
        client.post(f"/api/chapters/{chapter_id}/images", files={"image": pdf}).status_code == 415
    )
