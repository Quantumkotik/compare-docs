"""FastAPI-приложение: раздаёт веб-интерфейс и принимает два .docx файла."""

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.docx_reader import DocxReadError, read_docx

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ на файл

app = FastAPI(title="compare-docs", docs_url="/api/docs", redoc_url=None)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


async def _read_upload(upload: UploadFile, label: str):
    if not upload.filename:
        raise HTTPException(400, f"{label}: файл не выбран")

    if not upload.filename.lower().endswith(".docx"):
        raise HTTPException(400, f"{label}: ожидается файл .docx, получен «{upload.filename}»")

    data = await upload.read()

    if not data:
        raise HTTPException(400, f"{label}: файл пуст")

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, f"{label}: файл больше {MAX_FILE_SIZE // 1024 // 1024} МБ")

    try:
        return read_docx(data, upload.filename)
    except DocxReadError as exc:
        raise HTTPException(400, f"{label}: {exc}") from exc


@app.post("/api/upload")
async def upload(
    left: UploadFile = File(...),
    right: UploadFile = File(...),
) -> dict:
    """Принимает два документа и возвращает их разобранное содержимое."""
    left_doc = await _read_upload(left, "Документ 1")
    right_doc = await _read_upload(right, "Документ 2")

    return {
        "left": left_doc.as_dict(),
        "right": right_doc.as_dict(),
    }


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
