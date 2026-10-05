# Automatic Question Generation System (Advanced)

Paste or upload study material and get questions with answers. Uses a pre-trained **FLAN-T5** model (no training), a **FastAPI** backend and an HTML/CSS/JS website.

## Features
- Question types: short answer, multiple choice (MCQ), true/false
- Difficulty: easy, medium, hard
- Automatic answers, quality score (0-100), duplicate removal
- Show/hide answers, copy, export to .txt and .pdf (with answer key)
- Upload .txt or .pdf notes

## Run
```bash
python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --reload
```
Open http://localhost:8000. The first start downloads the model (about 1 GB), then runs offline.

## Choose a model
| Model | Size | Use when |
|---|---|---|
| google/flan-t5-small | ~300 MB | slow laptop / low RAM |
| google/flan-t5-base (default) | ~1 GB | normal laptop |
| google/flan-t5-large | ~3 GB | best quality, 16 GB RAM or GPU |

Windows: `set QG_MODEL=google/flan-t5-large`  |  macOS/Linux: `export QG_MODEL=google/flan-t5-large`

## Tests (no model download needed)
```bash
python test_offline.py
python test_pipeline.py
```

## How it works
1. `text_preprocessing.py`: clean, validate, split sentences, build chunks (1/2/3 sentences for easy/medium/hard)
2. `question_generator.py`: FLAN-T5 writes questions, then answers each from its source passage; MCQ distractors come from the text; false statements are model-edited sentences
3. `utils.py`: cleaning, duplicate removal, quality score, MCQ options
4. `exporter.py`: PDF paper + answer key
5. `server.py`: API (`/api/generate`, `/api/export/pdf`, `/api/extract`, docs at `/docs`)

## Troubleshooting
- `torch` install fails: use the CPU command from pytorch.org
- Out of memory: use flan-t5-small
- Weak questions: use flan-t5-large and paste longer, factual text (100+ words)
- Port busy: `uvicorn server:app --port 8001`
