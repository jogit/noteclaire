from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.api.deps import SettingsDep
from app.services import photo_service

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/{chapter_id}/{name}")
def get_photo(chapter_id: int, name: str, settings: SettingsDep) -> FileResponse:
    path = photo_service.original_path(settings, chapter_id, name)
    return FileResponse(
        path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=31536000"}
    )
