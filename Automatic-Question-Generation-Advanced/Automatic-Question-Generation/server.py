"""FastAPI server: website + /api/generate, /api/export/pdf, /api/extract."""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import question_generator as qg
from exporter import build_pdf

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    qg.load_model()  # download/load once at startup
    yield


app = FastAPI(title="Automatic Question Generation", lifespan=lifespan)


class GenerateRequest(BaseModel):
    text: str
    num_questions: int = Field(5, ge=1, le=10)
    qtype: Literal["short", "mcq", "tf"] = "short"
    difficulty: Literal["easy", "medium", "hard"] = "medium"


class ExportRequest(BaseModel):
    items: list[dict]
    include_answers: bool = True
    title: str = "Question Paper"


@app.get("/api/health")
def health():
    return {"status": "ok", "model": qg.MODEL_NAME}


@app.post("/api/generate")
def generate(req: GenerateRequest):  # sync def -> runs in a worker thread
    try:
        items = qg.generate(req.text, req.num_questions, req.qtype, req.difficulty)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if not items:
        raise HTTPException(status_code=422, detail="No good questions could be generated. Try a longer or more factual passage.")
    return {"items": items, "requested": req.num_questions}


@app.post("/api/export/pdf")
def export_pdf(req: ExportRequest):
    if not req.items:
        raise HTTPException(status_code=422, detail="Nothing to export.")
    pdf = build_pdf(req.items, req.title, req.include_answers)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="questions.pdf"'})


@app.post("/api/extract")
def extract(file: UploadFile = File(...)):
    name = (file.filename or "").lower()
    data = file.file.read()
    if len(data) > 8_000_000:
        raise HTTPException(status_code=413, detail="File is too large (8 MB max).")
    if name.endswith(".pdf"):
        from io import BytesIO
        from pypdf import PdfReader
        try:
            text = " ".join((p.extract_text() or "") for p in PdfReader(BytesIO(data)).pages)
        except Exception:
            raise HTTPException(status_code=422, detail="Could not read this PDF. It may be scanned or protected.")
    elif name.endswith(".txt"):
        text = data.decode("utf-8", errors="ignore")
    else:
        raise HTTPException(status_code=415, detail="Upload a .txt or .pdf file.")
    if not text.strip():
        raise HTTPException(status_code=422, detail="No text found in this file.")
    return {"text": text}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")
