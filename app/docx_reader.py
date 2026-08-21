"""Чтение .docx: извлечение текста абзацев и таблиц."""

import io
from dataclasses import dataclass, field

from docx import Document
from docx.opc.exceptions import PackageNotFoundError


class DocxReadError(Exception):
    """Файл не является корректным .docx документом."""


@dataclass
class DocxContent:
    """Разобранное содержимое одного документа."""

    filename: str
    size_bytes: int
    paragraphs: list[str] = field(default_factory=list)
    tables: int = 0

    @property
    def text(self) -> str:
        return "\n".join(self.paragraphs)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    @property
    def char_count(self) -> int:
        return len(self.text)

    def as_dict(self, preview_paragraphs: int = 20) -> dict:
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "paragraphs": len(self.paragraphs),
            "tables": self.tables,
            "words": self.word_count,
            "chars": self.char_count,
            "preview": self.paragraphs[:preview_paragraphs],
            "truncated": len(self.paragraphs) > preview_paragraphs,
        }


def read_docx(data: bytes, filename: str) -> DocxContent:
    """Разбирает байты .docx файла.

    Пустые абзацы отбрасываются — они не несут смысла при сравнении.
    """
    try:
        document = Document(io.BytesIO(data))
    except PackageNotFoundError as exc:
        raise DocxReadError(f"«{filename}» не является документом .docx") from exc
    except Exception as exc:  # повреждённый архив, неожиданный XML и т.п.
        raise DocxReadError(f"Не удалось прочитать «{filename}»: {exc}") from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            line = " | ".join(c for c in cells if c)
            if line:
                paragraphs.append(line)

    return DocxContent(
        filename=filename,
        size_bytes=len(data),
        paragraphs=paragraphs,
        tables=len(document.tables),
    )
