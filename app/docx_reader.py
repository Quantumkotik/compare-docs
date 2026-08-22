"""Чтение .docx: извлечение текста и базовой статистики."""

from __future__ import annotations

import io

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.opc.exceptions import PackageNotFoundError


class DocxError(Exception):
    """Файл не является корректным .docx документом."""


def _iter_blocks(document):
    """Идёт по телу документа и отдаёт абзацы и таблицы в исходном порядке."""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _table_rows(table: Table) -> list[str]:
    """Строки таблицы в виде «ячейка | ячейка»."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return rows


def _is_heading(paragraph: Paragraph) -> bool:
    style = paragraph.style
    return bool(style is not None and style.name and style.name.startswith("Heading"))


def parse_docx(raw: bytes, filename: str) -> dict:
    """Разбирает .docx из байтов и возвращает словарь с содержимым и статистикой."""
    try:
        document = Document(io.BytesIO(raw))
    except PackageNotFoundError as exc:
        raise DocxError(f"«{filename}» не является файлом .docx") from exc
    except Exception as exc:  # повреждённый архив, чужой формат и т.п.
        raise DocxError(f"Не удалось прочитать «{filename}»: {exc}") from exc

    lines: list[str] = []       # весь текст по порядку: абзацы и строки таблиц
    paragraphs: list[str] = []
    headings: list[str] = []
    table_count = 0

    for block in _iter_blocks(document):
        if isinstance(block, Table):
            table_count += 1
            lines.extend(_table_rows(block))
            continue

        text = block.text.strip()
        if not text:
            continue

        lines.append(text)
        paragraphs.append(text)

        if _is_heading(block):
            headings.append(text)

    text = "\n".join(lines)

    core = document.core_properties

    return {
        "filename": filename,
        "size_bytes": len(raw),
        "title": (core.title or "").strip() or None,
        "author": (core.author or "").strip() or None,
        "created": core.created.isoformat() if core.created else None,
        "modified": core.modified.isoformat() if core.modified else None,
        "paragraph_count": len(paragraphs),
        "table_count": table_count,
        "image_count": sum(
            1 for rel in document.part.rels.values() if "image" in rel.reltype
        ),
        "word_count": len(text.split()),
        "char_count": len(text),
        "headings": headings[:50],
        "lines": lines,
    }
