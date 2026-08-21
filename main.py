import difflib
import io
import threading
import webbrowser

import uvicorn
from docx import Document
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

HOST = "127.0.0.1"
PORT = 8000

app = FastAPI(title="Compare Docs")
app.mount("/static", StaticFiles(directory="static"), name="static")


def extract_paragraphs(data: bytes) -> list[str]:
    document = Document(io.BytesIO(data))
    return [p.text for p in document.paragraphs]


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/api/compare")
async def compare(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    for f in (file1, file2):
        if not f.filename.lower().endswith(".docx"):
            raise HTTPException(400, f"Файл {f.filename} не является .docx документом")

    try:
        lines1 = extract_paragraphs(await file1.read())
        lines2 = extract_paragraphs(await file2.read())
    except Exception:
        raise HTTPException(400, "Не удалось прочитать один из документов. Убедитесь, что это корректный .docx файл")

    diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
        lines1,
        lines2,
        fromdesc=file1.filename,
        todesc=file2.filename,
        context=False,
    )

    return {
        "filename1": file1.filename,
        "filename2": file2.filename,
        "identical": lines1 == lines2,
        "diff_html": diff_html,
    }


def open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")

# TODO: test
if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host=HOST, port=PORT)
