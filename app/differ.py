"""Сравнение двух документов: выравнивание абзацев и подсветка правок."""

import logging
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.docx_reader import DocxContent
from app.logging_setup import Step

log = logging.getLogger("app.differ")

# Длина фрагмента абзаца в отладочных строках лога
PREVIEW_LEN = 60

# Порог схожести, при котором два абзаца считаются одним изменённым,
# а не парой «удалён + добавлен».
SIMILARITY_THRESHOLD = 0.45

# Предел размера блока замен, на котором ещё считаем полное выравнивание
MAX_ALIGN_CELLS = 4000

_TOKEN_RE = re.compile(r"\S+|\s+")


@dataclass
class Span:
    """Фрагмент строки: text плюс пометка о правке."""

    text: str
    mark: str = "none"  # none | del | ins

    def as_dict(self) -> dict:
        return {"text": self.text, "mark": self.mark}


@dataclass
class Row:
    """Одна строка одной из колонок.

    kind: equal — без изменений, removed — пропало, added — появилось,
    changed — правка внутри абзаца, gap — пустое место для выравнивания.
    """

    kind: str
    spans: list[Span] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"kind": self.kind, "spans": [s.as_dict() for s in self.spans]}


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


def _preview(text: str) -> str:
    """Укороченный фрагмент абзаца для отладочных сообщений."""
    text = " ".join(text.split())
    return text if len(text) <= PREVIEW_LEN else text[:PREVIEW_LEN] + "…"


def _gap() -> Row:
    return Row("gap")


def _plain(kind: str, text: str, mark: str = "none") -> Row:
    return Row(kind, [Span(text, mark)])


def _word_diff(old: str, new: str) -> tuple[Row, Row]:
    """Пословный diff двух похожих абзацев."""
    old_tokens = _TOKEN_RE.findall(old)
    new_tokens = _TOKEN_RE.findall(new)

    matcher = SequenceMatcher(
        None,
        [t.casefold() for t in old_tokens],
        [t.casefold() for t in new_tokens],
        autojunk=False,
    )

    left_spans: list[Span] = []
    right_spans: list[Span] = []
    edits = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_part = "".join(old_tokens[i1:i2])
        new_part = "".join(new_tokens[j1:j2])

        if tag == "equal":
            left_spans.append(Span(old_part))
            right_spans.append(Span(new_part))
            continue

        edits += 1
        if tag == "delete":
            left_spans.append(Span(old_part, "del"))
            log.debug("    слова: удалено «%s»", _preview(old_part))
        elif tag == "insert":
            right_spans.append(Span(new_part, "ins"))
            log.debug("    слова: добавлено «%s»", _preview(new_part))
        else:  # replace
            left_spans.append(Span(old_part, "del"))
            right_spans.append(Span(new_part, "ins"))
            log.debug(
                "    слова: «%s» → «%s»", _preview(old_part), _preview(new_part)
            )

    log.debug("  пословный diff: правок %d", edits)
    return Row("changed", left_spans), Row("changed", right_spans)


def _align_block(old: list[str], new: list[str]) -> list[tuple[int | None, int | None]]:
    """Сопоставляет абзацы блока замен, сохраняя их порядок.

    Динамическое программирование максимизирует суммарную схожесть пар:
    абзац может быть соединён с наиболее близким по смыслу, а не просто
    с тем, что оказался напротив по номеру. Возвращает пары индексов,
    где None означает «пары нет» (абзац только удалён или только добавлен).
    """
    n, m = len(old), len(new)

    # На больших блоках DP не окупается — там всё равно почти нет общих строк
    if n * m > MAX_ALIGN_CELLS:
        log.info(
            "Блок замен %dx%d превышает предел %d ячеек — выравнивание пропущено",
            n,
            m,
            MAX_ALIGN_CELLS,
        )
        return [(i, None) for i in range(n)] + [(None, j) for j in range(m)]

    log.debug("Выравнивание блока замен: %d старых абзацев против %d новых", n, m)

    # score[i][j] — лучшая суммарная схожесть для хвостов old[i:] и new[j:]
    score = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = max(score[i + 1][j], score[i][j + 1])
            similarity = _similarity(old[i], new[j])
            if similarity >= SIMILARITY_THRESHOLD:
                best = max(best, similarity + score[i + 1][j + 1])
            score[i][j] = best

    pairs: list[tuple[int | None, int | None]] = []
    i = j = 0
    while i < n and j < m:
        similarity = _similarity(old[i], new[j])
        if similarity >= SIMILARITY_THRESHOLD and score[i][j] == similarity + score[i + 1][j + 1]:
            pairs.append((i, j))
            i += 1
            j += 1
        elif score[i + 1][j] >= score[i][j + 1]:
            pairs.append((i, None))
            i += 1
        else:
            pairs.append((None, j))
            j += 1

    pairs.extend((i, None) for i in range(i, n))
    pairs.extend((None, j) for j in range(j, m))
    return pairs


def _diff_replace_block(
    old: list[str],
    new: list[str],
    rows: list[tuple[Row, Row]],
) -> None:
    """Разбирает блок взаимно заменённых абзацев.

    Похожие абзацы соединяются в пару с пословной подсветкой, непохожие
    расходятся на «удалён» и «добавлен» — каждый напротив пустого места.
    """
    for i, j in _align_block(old, new):
        if i is not None and j is not None:
            log.debug(
                "  пара (схожесть %.2f): «%s» ↔ «%s»",
                _similarity(old[i], new[j]),
                _preview(old[i]),
                _preview(new[j]),
            )
            rows.append(_word_diff(old[i], new[j]))
        elif i is not None:
            log.debug("  без пары, удалён: «%s»", _preview(old[i]))
            rows.append((_plain("removed", old[i], "del"), _gap()))
        else:
            log.debug("  без пары, добавлен: «%s»", _preview(new[j]))
            rows.append((_gap(), _plain("added", new[j], "ins")))


def diff_documents(left: DocxContent, right: DocxContent) -> dict:
    """Строит выровненное построчное сравнение двух документов."""
    old = left.paragraphs
    new = right.paragraphs

    log.info(
        "Сравнение «%s» (%d абз.) с «%s» (%d абз.)",
        left.filename,
        len(old),
        right.filename,
        len(new),
    )

    with Step(log, "выравнивание абзацев") as step:
        matcher = SequenceMatcher(
            None,
            [_normalize(p) for p in old],
            [_normalize(p) for p in new],
            autojunk=False,
        )
        opcodes = matcher.get_opcodes()
        step.add(блоков=len(opcodes), схожесть=f"{matcher.ratio():.2f}")

    rows: list[tuple[Row, Row]] = []

    with Step(log, "построение строк сравнения") as step:
        for tag, i1, i2, j1, j2 in opcodes:
            log.debug("Блок %-7s старые [%d:%d] новые [%d:%d]", tag, i1, i2, j1, j2)

            if tag == "equal":
                for i, j in zip(range(i1, i2), range(j1, j2)):
                    rows.append((_plain("equal", old[i]), _plain("equal", new[j])))
            elif tag == "delete":
                for i in range(i1, i2):
                    log.debug("  удалён абзац %d: «%s»", i, _preview(old[i]))
                    rows.append((_plain("removed", old[i], "del"), _gap()))
            elif tag == "insert":
                for j in range(j1, j2):
                    log.debug("  добавлен абзац %d: «%s»", j, _preview(new[j]))
                    rows.append((_gap(), _plain("added", new[j], "ins")))
            else:
                _diff_replace_block(old[i1:i2], new[j1:j2], rows)

        step.add(строк=len(rows))

    summary = {
        "equal": sum(1 for l, _ in rows if l.kind == "equal"),
        "removed": sum(1 for l, _ in rows if l.kind == "removed"),
        "added": sum(1 for _, r in rows if r.kind == "added"),
        "changed": sum(1 for l, _ in rows if l.kind == "changed"),
    }
    summary["identical"] = summary["removed"] == summary["added"] == summary["changed"] == 0

    if summary["identical"]:
        log.info("Итог: документы идентичны, %d абзацев", summary["equal"])
    else:
        log.info(
            "Итог: удалено %d, добавлено %d, изменено %d, без изменений %d",
            summary["removed"],
            summary["added"],
            summary["changed"],
            summary["equal"],
        )

    return {
        "summary": summary,
        "rows": [{"left": l.as_dict(), "right": r.as_dict()} for l, r in rows],
    }
