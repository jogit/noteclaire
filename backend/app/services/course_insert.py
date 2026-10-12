"""Insertion d'un complément dans le cours sans casser sa mise en forme Markdown.

Le complément est ajouté après le bloc qui contient le passage cité :
- paragraphe (même écrit sur plusieurs lignes) : nouveau paragraphe après lui ;
- tableau : nouveau paragraphe après le tableau (sinon il serait coupé en deux) ;
- liste : un point de plus juste après l'élément, si le complément tient sur une ligne ;
  sinon un paragraphe après la liste (une liste numérotée ne repart pas à 1) ;
- bloc de formule ($$) ou de code (```) : après la fin du bloc ;
- encadré (:::) : à l'intérieur, après le paragraphe cité.
"""

import re

LIST_ITEM = re.compile(r"^(\s*)(?:([-*+])|(\d+)([.)]))\s+")
FENCES = ("```", "$$")


def _is_block_start(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith((":::", "#", "|", "```", "$$", ">"))
        or LIST_ITEM.match(line) is not None
    )


def _fence_end(lines: list[str], index: int) -> int | None:
    """Si la ligne `index` est dans un bloc ``` ou $$, renvoie la ligne qui le ferme."""
    open_fence: str | None = None
    start = 0
    for number, line in enumerate(lines):
        stripped = line.strip()
        if open_fence is None:
            for fence in FENCES:
                # « $$ … $$ » sur une seule ligne n'ouvre pas de bloc.
                if stripped.startswith(fence) and not (
                    fence == "$$" and len(stripped) > 2 and stripped.endswith("$$")
                ):
                    open_fence, start = fence, number
                    break
        elif stripped.startswith(open_fence) or (open_fence == "$$" and stripped.endswith("$$")):
            if start <= index <= number:
                return number
            open_fence = None
        if number > index and open_fence is None:
            return None
    return None


def _insert_lines(lines: list[str], after: int, new: list[str]) -> str:
    return "\n".join(lines[: after + 1] + new + lines[after + 1 :])


def _insert_paragraph(lines: list[str], after: int, addition: str) -> str:
    before = "\n".join(lines[: after + 1]).rstrip("\n")
    rest = "\n".join(lines[after + 1 :]).lstrip("\n")
    if not rest:
        return f"{before}\n\n{addition}\n"
    # Fin d'encadré (« ::: » seul) : collée au complément, comme on l'écrirait à la main.
    closes_callout = rest.split("\n", 1)[0].strip() == ":::"
    return f"{before}\n\n{addition}\n" + ("" if closes_callout else "\n") + rest


def _list_end(lines: list[str], index: int, indent: int) -> int:
    """Dernière ligne de la liste qui contient la ligne `index`."""
    last = index
    number = index + 1
    while number < len(lines):
        line = lines[number]
        if not line.strip():
            # Une ligne vide ne termine la liste que si la suite n'en fait plus partie.
            following = next((n for n in range(number, len(lines)) if lines[n].strip()), None)
            if following is None:
                break
            item = LIST_ITEM.match(lines[following])
            indented = len(lines[following]) - len(lines[following].lstrip()) > indent
            if not (item and len(item.group(1)) >= indent) and not indented:
                break
            number = following
            continue
        item = LIST_ITEM.match(line)
        if item and len(item.group(1)) < indent:
            break
        if not item and _is_block_start(line) and not line.startswith(" "):
            break
        last = number
        number += 1
    return last


def _table_end(lines: list[str], index: int) -> int:
    last = index
    while last + 1 < len(lines) and lines[last + 1].strip().startswith("|"):
        last += 1
    return last


def _list_item_start(lines: list[str], index: int) -> int:
    """Remonte à la ligne qui commence l'élément de liste contenant la ligne `index`."""
    start = index
    while (
        start > 0
        and not LIST_ITEM.match(lines[start])
        and lines[start].strip()
        and (not _is_block_start(lines[start]))
    ):
        start -= 1
    return start


def _item_end(lines: list[str], start: int, indent: int) -> int:
    """Fin de l'élément : ses lignes de suite et ses sous-éléments."""
    last = start
    while last + 1 < len(lines):
        following = lines[last + 1]
        sub = LIST_ITEM.match(following)
        if not following.strip() or (sub and len(sub.group(1)) <= indent):
            break
        if not sub and _is_block_start(following):
            break
        last += 1
    return last


def _insert_in_list(lines: list[str], start: int, item: re.Match[str], addition: str) -> str:
    indent = len(item.group(1))
    if "\n" not in addition and not _is_block_start(addition):
        # Puce identique, ou numéro suivant pour une liste numérotée.
        bullet = item.group(2)
        marker = bullet or f"{int(item.group(3)) + 1}{item.group(4)}"
        last = _item_end(lines, start, indent)
        return _insert_lines(lines, last, [f"{item.group(1)}{marker} {addition}"])
    return _insert_paragraph(lines, _list_end(lines, start, indent), addition)


def _paragraph_end(lines: list[str], index: int) -> int:
    """Un paragraphe peut tenir sur plusieurs lignes : jusqu'à la prochaine ligne vide."""
    last = index
    while (
        last + 1 < len(lines) and lines[last + 1].strip() and not _is_block_start(lines[last + 1])
    ):
        last += 1
    return last


def insert_addition(content: str, passage_end: int, addition: str) -> str:
    """Ajoute `addition` après le bloc qui contient la fin du passage cité."""
    addition = addition.strip()
    lines = content.split("\n")
    index = content.count("\n", 0, max(0, passage_end - 1))

    fence_end = _fence_end(lines, index)
    if fence_end is not None:
        return _insert_paragraph(lines, fence_end, addition)
    if lines[index].strip().startswith("|"):
        return _insert_paragraph(lines, _table_end(lines, index), addition)

    start = _list_item_start(lines, index)
    item = LIST_ITEM.match(lines[start])
    if item:
        return _insert_in_list(lines, start, item, addition)
    return _insert_paragraph(lines, _paragraph_end(lines, index), addition)
