from app.prompts import render_prompt


def test_values_are_not_reinterpreted() -> None:
    out = render_prompt(
        "explain",
        subject="X",
        level="y",
        chapter="c",
        course="a {{ passage }} b",
        adaptations="",
        passage="SECRET",
        request="r",
    )
    assert "a {{ passage }} b" in out
