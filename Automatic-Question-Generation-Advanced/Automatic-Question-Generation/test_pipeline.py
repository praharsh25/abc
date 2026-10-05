"""Tests the whole pipeline and API with a fake model (no download): python test_pipeline.py"""
import re
import question_generator as qg
from utils import clean_question

TEXT = ("Photosynthesis is the process by which green plants convert light energy into chemical energy. "
        "Chlorophyll, found in the chloroplasts, absorbs sunlight and helps plants produce glucose and oxygen. "
        "The light-dependent reactions take place in the thylakoid membranes and produce ATP and NADPH. "
        "The Calvin cycle then uses ATP and NADPH in the stroma to fix carbon dioxide into glucose. "
        "Oxygen is released into the atmosphere as a by-product when water molecules are split.")


def fake_run(prompts, per=1, beams=4, max_new=48):
    out = []
    for p in prompts:
        body = p.split("\n\n", 1)[1]
        if p.startswith("Answer the question"):
            passage = body.split("Question:")[0]
            out.append([re.findall(r"[A-Za-z]{6,}", passage)[-1]])
        elif p.startswith("Rewrite the sentence"):
            out.append([body.replace(body.split()[0], "Animals", 1)])
        else:
            w = re.findall(r"[A-Za-z]{7,}", body)
            out.append([f"What is said about {w[k % len(w)]} in the text" for k in range(per)])
    return out


qg._run = fake_run
qg.load_model = lambda: None

short = qg.generate(TEXT, 3, "short", "medium")
assert 1 <= len(short) <= 3 and all(i["answer"] and 0 <= i["score"] <= 100 for i in short), short
mcq = qg.generate(TEXT, 3, "mcq", "easy")
for i in mcq:
    assert len(i["options"]) == 4 and i["options"][i["correct_index"]].lower() == i["answer"].lower() and len(set(o.lower() for o in i["options"])) == 4, i
tf = qg.generate(TEXT, 4, "tf", "hard")
assert {i["answer"] for i in tf} == {"True", "False"}, tf
print(f"pipeline ok: {len(short)} short, {len(mcq)} mcq, {len(tf)} true/false")

from fastapi.testclient import TestClient
import server
with TestClient(server.app) as c:
    assert c.get("/").status_code == 200 and c.get("/api/health").json()["status"] == "ok"
    r = c.post("/api/generate", json={"text": TEXT, "num_questions": 3, "qtype": "mcq", "difficulty": "easy"})
    assert r.status_code == 200 and r.json()["items"], r.text
    assert c.post("/api/generate", json={"text": "short", "num_questions": 3}).status_code == 422
    assert c.post("/api/generate", json={"text": TEXT, "qtype": "bad"}).status_code == 422
    pdf = c.post("/api/export/pdf", json={"items": r.json()["items"] + tf, "include_answers": True})
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    up = c.post("/api/extract", files={"file": ("n.txt", TEXT.encode())})
    assert up.json()["text"].startswith("Photosynthesis")
    assert c.post("/api/extract", files={"file": ("n.docx", b"x")}).status_code == 415
print("API ok (generate, validation, pdf export, upload)")
