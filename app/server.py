"""FastAPI-приложение: раздаёт веб-интерфейс и принимает два .docx файла."""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.differ import diff_documents
from app.docx_reader import DocxContent, DocxReadError, read_docx
from app.logging_setup import Step, request_id, setup_logging

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ на файл

setup_logging()
log = logging.getLogger("app.server")

@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("Приложение запущено, статика: %s", STATIC_DIR)
    log.info("Ограничение на файл: %d МБ", MAX_FILE_SIZE // 1024 // 1024)
    yield
    log.info("Приложение остановлено")


app = FastAPI(
    title="compare-docs",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Присваивает запросу id, логирует его начало, итог и длительность.

    Заодно запрещает кэширование: иначе браузер продолжает крутить старую
    версию app.js после обновления кода и стучится в исчезнувшие эндпоинты.
    """
    token = request_id.set(uuid.uuid4().hex[:8])
    started = time.perf_counter()

    log.info("→ %s %s от %s", request.method, request.url.path, request.client.host)

    try:
        response = await call_next(request)
    except Exception:
        elapsed = (time.perf_counter() - started) * 1000
        log.exception("✗ %s %s упал за %.1f мс", request.method, request.url.path, elapsed)
        request_id.reset(token)
        raise

    elapsed = (time.perf_counter() - started) * 1000
    level = logging.WARNING if response.status_code >= 400 else logging.INFO
    log.log(
        level,
        "← %s %s → %d за %.1f мс",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    response.headers["Cache-Control"] = "no-store, must-revalidate"
    response.headers["X-Request-Id"] = request_id.get()
    request_id.reset(token)
    return response


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    log.debug("Отдаём index.html")
    return FileResponse(STATIC_DIR / "index.html")


async def _read_upload(upload: UploadFile, label: str) -> DocxContent:
    """Проверяет загруженный файл и разбирает его, логируя каждый шаг."""
    log.info("%s: получен файл «%s», тип %s", label, upload.filename, upload.content_type)

    if not upload.filename:
        log.warning("%s: имя файла пустое", label)
        raise HTTPException(400, f"{label}: файл не выбран")

    if not upload.filename.lower().endswith(".docx"):
        log.warning("%s: расширение не .docx — «%s»", label, upload.filename)
        raise HTTPException(400, f"{label}: ожидается файл .docx, получен «{upload.filename}»")

    with Step(log, f"{label}: чтение тела запроса") as step:
        data = await upload.read()
        step.add(байт=len(data))

    if not data:
        log.warning("%s: файл «%s» пуст", label, upload.filename)
        raise HTTPException(400, f"{label}: файл пуст")

    if len(data) > MAX_FILE_SIZE:
        log.warning("%s: файл «%s» — %d байт, превышен лимит", label, upload.filename, len(data))
        raise HTTPException(413, f"{label}: файл больше {MAX_FILE_SIZE // 1024 // 1024} МБ")

    log.debug("%s: проверки пройдены, переходим к разбору", label)

    try:
        return read_docx(data, upload.filename)
    except DocxReadError as exc:
        log.warning("%s: разбор не удался — %s", label, exc)
        raise HTTPException(400, f"{label}: {exc}") from exc


@app.post("/api/compare")
async def compare(
    left: UploadFile = File(...),
    right: UploadFile = File(...),
) -> dict:
    """Принимает старую и новую версии документа и возвращает их сравнение."""
    log.info("Начато сравнение: «%s» → «%s»", left.filename, right.filename)

    with Step(log, "обработка запроса на сравнение") as step:
        left_doc = await _read_upload(left, "Старая версия")
        right_doc = await _read_upload(right, "Новая версия")

        with Step(log, "построение diff"):
            result = diff_documents(left_doc, right_doc)

        step.add(строк=len(result["rows"]))

    log.info("Ответ готов: %s", result["summary"])

    return {
        "left": left_doc.as_dict(),
        "right": right_doc.as_dict(),
        **result,
    }


@app.post("/api/upload", include_in_schema=False)
async def stale_upload() -> dict:
    """Эндпоинт прошлой версии: сюда стучится страница из кэша браузера."""
    log.warning("Запрос к устаревшему /api/upload — у клиента страница из кэша")
    raise HTTPException(410, "Страница устарела — обновите её (Ctrl+F5) и повторите")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
