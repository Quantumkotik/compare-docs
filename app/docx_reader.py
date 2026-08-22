"""Чтение .docx: извлечение текста абзацев и таблиц."""

import io
import logging
from dataclasses import dataclass, field

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from app.logging_setup import Step

log = logging.getLogger("app.docx")


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

    def as_dict(self) -> dict:
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "paragraphs": len(self.paragraphs),
            "tables": self.tables,
            "words": self.word_count,
            "chars": self.char_count,
        }


def read_docx(data: bytes, filename: str) -> DocxContent:
    """Разбирает байты .docx файла.

    Пустые абзацы отбрасываются — они не несут смысла при сравнении.
    """
    log.info("Разбор документа «%s», %d байт", filename, len(data))

    with Step(log, f"открытие «{filename}»"):
        try:
            document = Document(io.BytesIO(data))
        except PackageNotFoundError as exc:
            log.warning("«%s»: не распознан как zip-контейнер docx", filename)
            raise DocxReadError(f"«{filename}» не является документом .docx") from exc
        except Exception as exc:  # повреждённый архив, неожиданный XML и т.п.
            log.exception("«%s»: сбой при открытии", filename)
            raise DocxReadError(f"Не удалось прочитать «{filename}»: {exc}") from exc

    with Step(log, f"извлечение абзацев из «{filename}»") as step:
        raw_count = len(document.paragraphs)
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        step.add(всего=raw_count, непустых=len(paragraphs))
        log.debug("«%s»: отброшено пустых абзацев: %d", filename, raw_count - len(paragraphs))

    with Step(log, f"извлечение таблиц из «{filename}»") as step:
        table_lines = 0
        for index, table in enumerate(document.tables, 1):
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                line = " | ".join(c for c in cells if c)
                if line:
                    paragraphs.append(line)
                    table_lines += 1
            log.debug("«%s»: таблица %d — строк %d", filename, index, len(table.rows))
        step.add(таблиц=len(document.tables), строк=table_lines)

    content = DocxContent(
        filename=filename,
        size_bytes=len(data),
        paragraphs=paragraphs,
        tables=len(document.tables),
    )
    log.info(
        "Документ «%s» разобран: абзацев %d, слов %d, символов %d",
        filename,
        len(content.paragraphs),
        content.word_count,
        content.char_count,
    )
    return content
