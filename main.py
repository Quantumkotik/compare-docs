"""Веб-приложение для сравнения двух docx-документов.

Запуск: python main.py — поднимает сервер и открывает браузер.

Логи пишутся в консоль и в файл logs/app.log. Уровень задаётся
переменной окружения LOG_LEVEL (по умолчанию DEBUG).
"""

import io
import logging
import os
import re
import sys
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from pathlib import Path

import uvicorn
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
LOG_DIR = BASE_DIR / "logs"

HOST = "127.0.0.1"
PORT = 8000

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ

# Ниже этого сходства строки считаются не изменённой парой,
# а полным удалением слева и полной вставкой справа.
SIMILARITY_THRESHOLD = 0.5


def setup_logging() -> logging.Logger:
    """Настраивает вывод логов в консоль и в файл logs/app.log."""
    LOG_DIR.mkdir(exist_ok=True)

    level = getattr(logging, os.getenv("LOG_LEVEL", "DEBUG").upper(), logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [console, file_handler]

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [console, file_handler]
        # Без этого запись уходит ещё и в корневой логгер — строки дублируются.
        uvicorn_logger.propagate = False

    return logging.getLogger("compare")


log = setup_logging()

app = FastAPI(title="Compare Docs")


def assets_version() -> str:
    """Версия статики по времени изменения файлов — для сброса кеша."""
    stamps = []
    for name in ("app.js", "style.css"):
        path = STATIC_DIR / name
        stamps.append(int(path.stat().st_mtime) if path.exists() else 0)
    return str(max(stamps))


@app.middleware("http")
async def log_and_no_cache(request: Request, call_next):
    """Логирует каждый HTTP-запрос и запрещает кеширование фронтенда."""
    started = time.perf_counter()
    client = f"{request.client.host}:{request.client.port}" if request.client else "-"
    log.info("→ %s %s от %s", request.method, request.url.path, client)

    response = await call_next(request)

    elapsed = (time.perf_counter() - started) * 1000
    log.info(
        "← %s %s → %s за %.1f мс",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    if not request.url.path.startswith("/api/"):
        # Иначе браузер держит старые index.html/app.js и шлёт запросы
        # на эндпоинты, которых в текущей версии уже нет.
        response.headers["Cache-Control"] = "no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def iter_blocks(document: Document):
    """Идёт по телу документа в исходном порядке: абзацы и таблицы."""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def extract_lines(document: Document, label: str) -> list[str]:
    """Собирает текстовые строки документа: абзацы и строки таблиц."""
    lines = []
    paragraphs = tables = table_rows = 0
    for block in iter_blocks(document):
        if isinstance(block, Paragraph):
            paragraphs += 1
            text = block.text.strip()
            if text:
                lines.append(text)
        else:
            tables += 1
            for row in block.rows:
                cells = [cell.text.strip() for cell in row.cells]
                if any(cells):
                    table_rows += 1
                    lines.append(" | ".join(cells))
    log.debug(
        "[%s] блоков разобрано: абзацев %s, таблиц %s (строк в них %s) → строк с текстом %s",
        label,
        paragraphs,
        tables,
        table_rows,
        len(lines),
    )
    return lines


def parse_docx(upload: UploadFile, raw: bytes, label: str) -> tuple[list[str], dict]:
    """Проверяет и разбирает docx, возвращает строки и сводку по файлу."""
    log.info(
        "[%s] получен файл «%s», content-type=%s, размер %s байт",
        label,
        upload.filename,
        upload.content_type,
        len(raw),
    )

    if not upload.filename.lower().endswith(".docx"):
        log.warning("[%s] отклонён: расширение не .docx", label)
        raise HTTPException(
            status_code=400,
            detail=f"Файл «{upload.filename}» не является документом .docx",
        )
    if len(raw) > MAX_FILE_SIZE:
        log.warning("[%s] отклонён: %s байт > лимита %s", label, len(raw), MAX_FILE_SIZE)
        raise HTTPException(
            status_code=400,
            detail=f"Файл «{upload.filename}» больше 20 МБ",
        )

    started = time.perf_counter()
    try:
        document = Document(io.BytesIO(raw))
    except PackageNotFoundError:
        log.warning("[%s] отклонён: не открывается как docx-пакет", label)
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать файл «{upload.filename}»: повреждён или не docx",
        )
    log.debug("[%s] docx открыт за %.1f мс", label, (time.perf_counter() - started) * 1000)

    lines = extract_lines(document, label)
    stats = {
        "filename": upload.filename,
        "size": len(raw),
        "lines": len(lines),
        "words": sum(len(line.split()) for line in lines),
    }
    log.info("[%s] разобран: строк %s, слов %s", label, stats["lines"], stats["words"])
    return lines, stats


def split_words(text: str) -> list[str]:
    """Режет строку на слова вместе с идущими за ними пробелами."""
    return re.findall(r"\S+\s*|\s+", text)


def diff_words(old: str, new: str) -> tuple[list[dict], list[dict]]:
    """Пословный diff двух строк: какие куски убрали слева и добавили справа."""
    old_words = split_words(old)
    new_words = split_words(new)
    matcher = SequenceMatcher(None, old_words, new_words, autojunk=False)

    old_parts: list[dict] = []
    new_parts: list[dict] = []

    def append(parts: list[dict], text: str, changed: bool) -> None:
        if not text:
            return
        if parts and parts[-1]["changed"] == changed:
            parts[-1]["text"] += text
        else:
            parts.append({"text": text, "changed": changed})

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        old_chunk = "".join(old_words[i1:i2])
        new_chunk = "".join(new_words[j1:j2])
        if tag == "equal":
            append(old_parts, old_chunk, False)
            append(new_parts, new_chunk, False)
        else:
            append(old_parts, old_chunk, True)
            append(new_parts, new_chunk, True)

    return old_parts, new_parts


def whole(text: str) -> list[dict]:
    return [{"text": text, "changed": True}]


def unchanged(text: str) -> list[dict]:
    return [{"text": text, "changed": False}]


def make_rows(old_lines: list[str], new_lines: list[str]) -> tuple[list[dict], dict]:
    """Строит выровненные строки side-by-side diff и сводку изменений."""
    log.info("Сравниваю: слева %s строк, справа %s строк", len(old_lines), len(new_lines))
    started = time.perf_counter()

    matcher = SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    opcodes = matcher.get_opcodes()
    log.debug("Блоков различий найдено: %s", len(opcodes))

    rows: list[dict] = []
    summary = {"unchanged": 0, "removed": 0, "added": 0, "changed": 0}
    old_no = new_no = 0

    def side(number: int, parts: list[dict], kind: str) -> dict:
        return {"number": number, "parts": parts, "type": kind}

    for tag, i1, i2, j1, j2 in opcodes:
        log.debug("Блок %-7s строки слева %s..%s, справа %s..%s", tag, i1, i2, j1, j2)

        if tag == "equal":
            for offset in range(i2 - i1):
                old_no += 1
                new_no += 1
                text = old_lines[i1 + offset]
                rows.append(
                    {
                        "old": side(old_no, unchanged(text), "equal"),
                        "new": side(new_no, unchanged(text), "equal"),
                    }
                )
                summary["unchanged"] += 1
            continue

        old_chunk = old_lines[i1:i2]
        new_chunk = new_lines[j1:j2]

        for index in range(max(len(old_chunk), len(new_chunk))):
            old_text = old_chunk[index] if index < len(old_chunk) else None
            new_text = new_chunk[index] if index < len(new_chunk) else None

            if old_text is not None and new_text is not None:
                old_no += 1
                new_no += 1
                ratio = SequenceMatcher(None, old_text, new_text).ratio()
                if ratio >= SIMILARITY_THRESHOLD:
                    old_parts, new_parts = diff_words(old_text, new_text)
                    changed_words = sum(1 for p in new_parts if p["changed"])
                    log.debug(
                        "  строка %s/%s изменена (сходство %.2f, изменённых кусков %s)",
                        old_no,
                        new_no,
                        ratio,
                        changed_words,
                    )
                    rows.append(
                        {
                            "old": side(old_no, old_parts, "changed"),
                            "new": side(new_no, new_parts, "changed"),
                        }
                    )
                    summary["changed"] += 1
                else:
                    log.debug(
                        "  строка %s удалена, строка %s добавлена (сходство %.2f)",
                        old_no,
                        new_no,
                        ratio,
                    )
                    rows.append(
                        {
                            "old": side(old_no, whole(old_text), "removed"),
                            "new": side(new_no, whole(new_text), "added"),
                        }
                    )
                    summary["removed"] += 1
                    summary["added"] += 1
            elif old_text is not None:
                old_no += 1
                log.debug("  строка %s удалена", old_no)
                rows.append(
                    {"old": side(old_no, whole(old_text), "removed"), "new": None}
                )
                summary["removed"] += 1
            else:
                new_no += 1
                log.debug("  строка %s добавлена", new_no)
                rows.append(
                    {"old": None, "new": side(new_no, whole(new_text), "added")}
                )
                summary["added"] += 1

    log.info(
        "Сравнение готово за %.1f мс: строк в выдаче %s, %s",
        (time.perf_counter() - started) * 1000,
        len(rows),
        summary,
    )
    return rows, summary


@app.post("/api/compare")
async def compare(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
) -> dict:
    """Принимает старую и новую версии документа и возвращает их различия."""
    log.info("=== Шаг 1: приём файлов ===")
    old_raw = await file1.read()
    new_raw = await file2.read()

    log.info("=== Шаг 2: разбор старой версии ===")
    old_lines, old_stats = parse_docx(file1, old_raw, "старая")

    log.info("=== Шаг 3: разбор новой версии ===")
    new_lines, new_stats = parse_docx(file2, new_raw, "новая")

    log.info("=== Шаг 4: построение diff ===")
    rows, summary = make_rows(old_lines, new_lines)

    log.info("=== Шаг 5: ответ отправлен ===")
    return {
        "old": old_stats,
        "new": new_stats,
        "rows": rows,
        "summary": summary,
    }


@app.post("/api/upload")
async def legacy_upload() -> JSONResponse:
    """Эндпоинт первой версии. Сюда стучится только устаревший app.js из кеша."""
    log.error(
        "Запрос на устаревший /api/upload — браузер выполняет старый app.js из кеша. "
        "Нужна перезагрузка страницы с очисткой кеша (Cmd+Shift+R)."
    )
    return JSONResponse(
        status_code=410,
        content={
            "detail": (
                "Страница открыта из кеша браузера и использует старую версию "
                "интерфейса. Обновите страницу с очисткой кеша: Cmd+Shift+R "
                "(Windows/Linux — Ctrl+F5)."
            )
        },
    )


@app.get("/")
async def index() -> HTMLResponse:
    """Отдаёт страницу, подставляя версию статики, чтобы сбросить кеш браузера."""
    version = assets_version()
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    log.debug("Отдаю index.html, версия статики v=%s", version)
    return HTMLResponse(html.replace("__V__", version))


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def on_startup() -> None:
    log.info("Каталог статики: %s", STATIC_DIR)
    log.info("Файл логов: %s", LOG_DIR / "app.log")
    for name in ("index.html", "app.js", "style.css"):
        path = STATIC_DIR / name
        log.info(
            "  %s — %s, изменён %s",
            name,
            "найден" if path.exists() else "ОТСУТСТВУЕТ",
            time.strftime("%d.%m %H:%M:%S", time.localtime(path.stat().st_mtime))
            if path.exists()
            else "-",
        )
    log.info("Версия статики: v=%s", assets_version())
    log.info("Приложение готово принимать документы")


def open_browser() -> None:
    log.info("Открываю браузер: http://%s:%s", HOST, PORT)
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT, log_config=None)
