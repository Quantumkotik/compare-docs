"""Веб-приложение для загрузки двух docx-документов.

Запуск: python main.py — поднимает сервер и открывает браузер.
"""

import io
import threading
import webbrowser
from pathlib import Path

import uvicorn
from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

HOST = "127.0.0.1"
PORT = 8000

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 МБ

app = FastAPI(title="Compare Docs")


def read_docx(upload: UploadFile, raw: bytes) -> dict:
    """Разбирает docx и возвращает краткую сводку по документу."""
    if not upload.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Файл «{upload.filename}» не является документом .docx",
        )
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл «{upload.filename}» больше 20 МБ",
        )

    try:
        document = Document(io.BytesIO(raw))
    except PackageNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось прочитать файл «{upload.filename}»: повреждён или не docx",
        )

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    text = "\n".join(paragraphs)

    return {
        "filename": upload.filename,
        "size": len(raw),
        "paragraphs": len(paragraphs),
        "tables": len(document.tables),
        "words": len(text.split()),
        "characters": len(text),
        "preview": text[:1000],
    }


@app.post("/api/upload")
async def upload(
    file1: UploadFile = File(...),
    file2: UploadFile = File(...),
) -> dict:
    """Принимает два docx-файла и возвращает сводку по каждому."""
    documents = []
    for upload_file in (file1, file2):
        raw = await upload_file.read()
        documents.append(read_docx(upload_file, raw))
    return {"documents": documents}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def open_browser() -> None:
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT)
