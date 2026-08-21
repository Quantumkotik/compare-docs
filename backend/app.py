from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .docx_utils import diff_paragraphs, extract_paragraphs

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="Compare Docs")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/api/compare")
async def compare(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    for f in (file1, file2):
        if not f.filename.lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail=f'«{f.filename}» не является файлом .docx')

    content1 = await file1.read()
    content2 = await file2.read()

    try:
        paragraphs1 = extract_paragraphs(content1)
        paragraphs2 = extract_paragraphs(content2)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Не удалось прочитать документ: {exc}")

    return {
        "file1": file1.filename,
        "file2": file2.filename,
        "diff": diff_paragraphs(paragraphs1, paragraphs2),
    }
