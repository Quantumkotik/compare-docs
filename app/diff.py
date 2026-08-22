"""Сравнение двух документов: выравнивание абзацев и различия по словам."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

# порог, ниже которого абзацы считаются не изменённой версией друг друга,
# а полностью разными (удалён один, добавлен другой)
ПОХОЖЕСТЬ_АБЗАЦЕВ = 0.4

# слово вместе с идущими за ним пробелами — склейка кусков возвращает исходный текст
_ТОКЕН = re.compile(r"\S+\s*", re.UNICODE)


def _токены(текст: str) -> list[str]:
    return _ТОКЕН.findall(текст)


def _нормализовать(текст: str) -> str:
    return " ".join(текст.split()).casefold()


def _похожесть(левый: str, правый: str) -> float:
    return SequenceMatcher(None, _нормализовать(левый), _нормализовать(правый)).ratio()


def _части_слов(старый: str, новый: str) -> tuple[list[dict], list[dict]]:
    """Разбивает пару абзацев на куски с пометкой изменённых слов."""
    старые_токены = _токены(старый)
    новые_токены = _токены(новый)

    слева: list[dict] = []
    справа: list[dict] = []

    matcher = SequenceMatcher(None, [t.strip().casefold() for t in старые_токены],
                              [t.strip().casefold() for t in новые_токены])

    for тег, и1, и2, ж1, ж2 in matcher.get_opcodes():
        старый_кусок = "".join(старые_токены[и1:и2])
        новый_кусок = "".join(новые_токены[ж1:ж2])

        if тег == "equal":
            слева.append({"text": старый_кусок, "changed": False})
            справа.append({"text": новый_кусок, "changed": False})
        else:
            if старый_кусок:
                слева.append({"text": старый_кусок, "changed": True})
            if новый_кусок:
                справа.append({"text": новый_кусок, "changed": True})

    return слева, справа


def _блок(текст: str, вид: str, части: list[dict] | None = None) -> dict:
    return {
        "text": текст,
        "kind": вид,  # equal | changed | removed | added
        "parts": части or [{"text": текст, "changed": False}],
    }


def _пара(старый: str, новый: str) -> dict:
    слева, справа = _части_слов(старый, новый)
    return {
        "kind": "changed",
        "left": _блок(старый, "changed", слева),
        "right": _блок(новый, "changed", справа),
    }


def _разные(старые: list[str], новые: list[str]) -> list[dict]:
    """Обрабатывает блок замены: пытается сопоставить абзацы попарно."""
    строки: list[dict] = []
    общие = min(len(старые), len(новые))

    for индекс in range(общие):
        старый, новый = старые[индекс], новые[индекс]
        if _похожесть(старый, новый) >= ПОХОЖЕСТЬ_АБЗАЦЕВ:
            строки.append(_пара(старый, новый))
        else:
            строки.append({"kind": "removed", "left": _блок(старый, "removed"), "right": None})
            строки.append({"kind": "added", "left": None, "right": _блок(новый, "added")})

    for старый in старые[общие:]:
        строки.append({"kind": "removed", "left": _блок(старый, "removed"), "right": None})

    for новый in новые[общие:]:
        строки.append({"kind": "added", "left": None, "right": _блок(новый, "added")})

    return строки


def сравнить(старые: list[str], новые: list[str]) -> dict:
    """Возвращает выровненные строки сравнения и сводную статистику."""
    matcher = SequenceMatcher(
        None,
        [_нормализовать(п) for п in старые],
        [_нормализовать(п) for п in новые],
    )

    строки: list[dict] = []

    for тег, и1, и2, ж1, ж2 in matcher.get_opcodes():
        if тег == "equal":
            for смещение in range(и2 - и1):
                текст_слева = старые[и1 + смещение]
                текст_справа = новые[ж1 + смещение]
                строки.append({
                    "kind": "equal",
                    "left": _блок(текст_слева, "equal"),
                    "right": _блок(текст_справа, "equal"),
                })
        elif тег == "delete":
            for текст in старые[и1:и2]:
                строки.append({"kind": "removed", "left": _блок(текст, "removed"), "right": None})
        elif тег == "insert":
            for текст in новые[ж1:ж2]:
                строки.append({"kind": "added", "left": None, "right": _блок(текст, "added")})
        else:  # replace
            строки.extend(_разные(старые[и1:и2], новые[ж1:ж2]))

    удалённые_слова = sum(
        len(_токены(часть["text"]))
        for строка in строки
        if строка["left"]
        for часть in строка["left"]["parts"]
        if часть["changed"] or строка["kind"] == "removed"
    )

    добавленные_слова = sum(
        len(_токены(часть["text"]))
        for строка in строки
        if строка["right"]
        for часть in строка["right"]["parts"]
        if часть["changed"] or строка["kind"] == "added"
    )

    статистика = {
        "equal": sum(1 for с in строки if с["kind"] == "equal"),
        "changed": sum(1 for с in строки if с["kind"] == "changed"),
        "removed": sum(1 for с in строки if с["kind"] == "removed"),
        "added": sum(1 for с in строки if с["kind"] == "added"),
        "words_removed": удалённые_слова,
        "words_added": добавленные_слова,
        "similarity": round(matcher.ratio(), 4),
    }

    return {"rows": строки, "stats": статистика}
