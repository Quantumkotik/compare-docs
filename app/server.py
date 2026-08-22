"""FastAPI-приложение: отдаёт веб-интерфейс и принимает два .docx документа."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.diff import сравнить
from app.docx_reader import DocxError, parse_docx

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 МБ на файл
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

app = FastAPI(title="Docx Uploader", docs_url="/api/docs", redoc_url=None)


async def _read_docx(upload: UploadFile) -> dict:
    filename = upload.filename or "без имени"

    if not filename.lower().endswith(".docx"):
        raise HTTPException(400, f"«{filename}»: поддерживаются только файлы .docx")

    raw = await upload.read()

    if not raw:
        raise HTTPException(400, f"«{filename}»: файл пустой")

    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(
            413, f"«{filename}»: файл больше {MAX_FILE_SIZE // (1024 * 1024)} МБ"
        )

    try:
        return parse_docx(raw, filename)
    except DocxError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/upload")
async def upload(
    first: UploadFile = File(..., description="Старая версия документа .docx"),
    second: UploadFile = File(..., description="Новая версия документа .docx"),
) -> dict:
    """Принимает две версии документа и возвращает их содержимое и различия."""
    старый = await _read_docx(first)
    новый = await _read_docx(second)

    return {
        "documents": [старый, новый],
        "diff": сравнить(старый["lines"], новый["lines"]),
    }


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
