from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .docx_utils import diff_paragraphs, extract_paragraphs

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


def _asset_version(filename: str) -> int:
    return int((FRONTEND_DIR / filename).stat().st_mtime)


class NoCacheStaticFiles(StaticFiles):
    """Always serve fresh files during local development.

    Without this, browsers cache /static/* by heuristic freshness (no
    explicit Cache-Control is set otherwise), so a plain refresh can keep
    running JS/CSS from before the latest backend restart.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-store"
        return response


app = FastAPI(title="Compare Docs")

app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Stamp static asset URLs with a version so a new deploy is never
    served from a browser's stale cache of the previous script/style."""
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("/static/style.css", f"/static/style.css?v={_asset_version('style.css')}")
    html = html.replace("/static/script.js", f"/static/script.js?v={_asset_version('script.js')}")
    return HTMLResponse(content=html, headers={"Cache-Control": "no-store"})


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
        "rows": diff_paragraphs(paragraphs1, paragraphs2),
    }
