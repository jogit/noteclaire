import asyncio

import pytest
from pydantic import BaseModel

from app.services.ai.base import AIResponse, CourseRequest, PhotoRequest, StructureRequest
from app.services.ai.prompted import PromptedProvider

NOTE = "Particularités de l'élève, à respecter : dyslexique"


class Capture(PromptedProvider):
    name = "capture"
    model = "capture"
    paid = False

    def __init__(self) -> None:
        self.prompt = ""

    async def _parse[T: BaseModel](
        self, prompt: str, schema: type[T], images: tuple[str, ...] = ()
    ) -> AIResponse[T]:
        self.prompt = prompt
        raise RuntimeError("prompt capturé")


@pytest.mark.parametrize(
    "ask",
    [
        lambda p: p.structure_course(
            StructureRequest(subject="s", chapter="c", raw_notes="n", adaptations=NOTE)
        ),
        lambda p: p.generate_quiz(
            CourseRequest(subject="s", chapter="c", course="x", adaptations=NOTE)
        ),
        lambda p: p.transcribe_photo(
            PhotoRequest(subject="s", chapter="c", image_data_url="data:,", adaptations=NOTE)
        ),
    ],
    ids=["mise au propre", "quiz", "photo"],
)
def test_the_students_particularities_reach_the_prompt(ask) -> None:  # type: ignore[no-untyped-def]
    provider = Capture()
    with pytest.raises(RuntimeError):
        asyncio.run(ask(provider))
    assert NOTE in provider.prompt
