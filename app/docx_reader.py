"""Чтение .docx: извлечение текста и базовой статистики."""

from __future__ import annotations

import io

from docx import Document
from docx.opc.exceptions import PackageNotFoundError


class DocxError(Exception):
    """Файл не является корректным .docx документом."""


def _iter_table_text(table) -> list[str]:
    rows = []
    for row in table.rows:
        cells = [cell.text.strip() for cell in row.cells]
        if any(cells):
            rows.append(" | ".join(cells))
    return rows


def parse_docx(raw: bytes, filename: str) -> dict:
    """Разбирает .docx из байтов и возвращает словарь с содержимым и статистикой."""
    try:
        document = Document(io.BytesIO(raw))
    except PackageNotFoundError as exc:
        raise DocxError(f"«{filename}» не является файлом .docx") from exc
    except Exception as exc:  # повреждённый архив, чужой формат и т.п.
        raise DocxError(f"Не удалось прочитать «{filename}»: {exc}") from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    headings = [
        p.text.strip()
        for p in document.paragraphs
        if p.style is not None
        and p.style.name
        and p.style.name.startswith("Heading")
        and p.text.strip()
    ]

    tables = [_iter_table_text(t) for t in document.tables]
    table_text = [line for table in tables for line in table]

    text = "\n".join(paragraphs + table_text)
    words = text.split()

    core = document.core_properties

    return {
        "filename": filename,
        "size_bytes": len(raw),
        "title": (core.title or "").strip() or None,
        "author": (core.author or "").strip() or None,
        "created": core.created.isoformat() if core.created else None,
        "modified": core.modified.isoformat() if core.modified else None,
        "paragraph_count": len(paragraphs),
        "table_count": len(document.tables),
        "image_count": sum(
            1 for rel in document.part.rels.values() if "image" in rel.reltype
        ),
        "word_count": len(words),
        "char_count": len(text),
        "headings": headings[:50],
        "paragraphs": paragraphs,
    }
