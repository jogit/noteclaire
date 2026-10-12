from dataclasses import asdict

from fastapi import APIRouter

from app.api.deps import DbDep, StudentDep
from app.schemas.api import SearchResultOut
from app.services import search_service

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
def search(db: DbDep, student: StudentDep, q: str = "") -> list[SearchResultOut]:
    return [SearchResultOut(**asdict(r)) for r in search_service.search(db, student.id, q)]
