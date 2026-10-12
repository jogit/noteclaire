from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import SettingsDep
from app.services import image_service

router = APIRouter(prefix="/api/images", tags=["images"])


@router.get("/{chapter_id}/{name}")
def get_image(chapter_id: int, name: str, settings: SettingsDep) -> FileResponse:
    path = image_service.image_path(settings, chapter_id, name)
    headers = {"Cache-Control": "private, max-age=31536000", "X-Content-Type-Options": "nosniff"}
    if path.suffix == ".svg":
        # Même nettoyé, un SVG ouvert à son adresse directe ne doit exécuter ni charger rien.
        headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        )
        return FileResponse(path, media_type="image/svg+xml", headers=headers)
    return FileResponse(path, media_type="image/jpeg", headers=headers)
