import math

import pytest

from app.errors import AppError
from app.services.ai.base import RedrawResult, SchemaArrow, SchemaLine, SchemaText
from app.services.schema_drawing import MAX_ELEMENTS, draw_schema


def scene(**kwargs: object) -> RedrawResult:
    values: dict[str, object] = {
        "inventory": [],
        "texts": [],
        "arrows": [],
        "lines": [],
        "corrections": [],
    } | kwargs
    return RedrawResult(**values)


def arrow(start: bool, end: bool, d: str = "M 10 10 C 20 40 60 40 90 10") -> SchemaArrow:
    return SchemaArrow(d=d, head_start=start, head_end=end, color="noir")


def test_arrowheads_are_exactly_those_asked_for() -> None:
    svg = draw_schema(
        scene(arrows=[arrow(True, True), arrow(False, True), arrow(False, False)]), 800, 400
    )
    paths = [p for p in svg.split("<path") if 'fill="none"' in p]
    assert [("marker-start" in p, "marker-end" in p) for p in paths] == [
        (True, True),
        (False, True),
        (False, False),
    ]
    assert 'viewBox="0 0 800 400"' in svg and 'orient="auto-start-reverse"' in svg


def test_texts_with_subscripts_and_superscripts() -> None:
    text = SchemaText(x=10, y=50, text="Ca(OH)_{2} (s) Ca^{2+}", size=30, color="noir")
    svg = draw_schema(scene(texts=[text]), 400, 100)
    assert 'font-size="21.0">2</tspan>' in svg  # indice plus petit, descendu
    assert 'dy="10.5"' in svg and 'dy="-10.5"' in svg and "2+</tspan>" in svg
    assert svg.count("<text") == 1


def test_text_is_escaped_never_interpreted() -> None:
    text = SchemaText(x=0, y=20, text='<script>alert("x")</script> & plus', size=24, color="noir")
    svg = draw_schema(scene(texts=[text]), 200, 50)
    assert "<script" not in svg and "&lt;script&gt;" in svg and "&amp; plus" in svg


@pytest.mark.parametrize(
    "bad_path",
    [
        "",
        "M 0 0 L javascript:alert(1)",
        'M 0 0" onload="x',
        "M 0 0 <script>",
        "M 0 0 url(#a)",
        "x" * 10,
    ],
)
def test_rejects_paths_that_are_not_drawing_commands(bad_path: str) -> None:
    with pytest.raises(AppError) as error:
        draw_schema(scene(lines=[SchemaLine(d=bad_path, color="noir")]), 100, 100)
    assert error.value.code == "schema_invalid"


def test_rejects_empty_oversized_or_non_finite_descriptions() -> None:
    for broken in (
        scene(),
        scene(lines=[SchemaLine(d="M 0 0 L 1 1", color="noir")] * (MAX_ELEMENTS + 1)),
        scene(texts=[SchemaText(x=math.inf, y=0, text="a", size=24, color="noir")]),
    ):
        with pytest.raises(AppError):
            draw_schema(broken, 100, 100)


def test_text_size_is_kept_readable() -> None:
    tiny = SchemaText(x=0, y=0, text="a", size=2, color="noir")
    assert 'font-size="12.0"' in draw_schema(scene(texts=[tiny]), 100, 100)


def test_colors_are_the_students_and_the_hand_style_embeds_its_font() -> None:
    texts = [SchemaText(x=5, y=30, text="état", size=24, color="bleu")]
    arrows = [SchemaArrow(d="M 0 0 L 9 9", head_start=False, head_end=True, color="vert")]
    plain = draw_schema(scene(texts=texts, arrows=arrows), 100, 60)
    hand = draw_schema(scene(texts=texts, arrows=arrows), 100, 60, hand=True)
    for svg in (plain, hand):
        assert 'fill="#2c3fb8"' in svg and 'stroke="#1f8a3d"' in svg
    assert "Caveat" not in plain and "tremble" not in plain
    assert "font-family:Caveat" in hand and "data:font/woff2;base64," in hand
    assert "http" not in hand.replace("http://www.w3.org/2000/svg", "")
