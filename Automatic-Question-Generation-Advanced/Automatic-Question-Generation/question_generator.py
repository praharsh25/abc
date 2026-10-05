"""FLAN-T5 question, answer, MCQ and true/false generation."""
import os
import random
import threading

from text_preprocessing import (clean_text, key_terms, make_chunks, split_sentences,
                                validate_text)
from utils import (clean_question, is_valid_question, make_options, overlap,
                   quality_score, remove_duplicates)

MODEL_NAME = os.getenv("QG_MODEL", "google/flan-t5-base")  # flan-t5-small for low RAM, flan-t5-large for quality
BATCH = 8
_lock = threading.RLock()
_tok = _model = None

DIFFICULTY = {
    "easy":   {"size": 1, "prompt": "Write a simple factual question (what, who, when or where) that can be answered using this passage:\n\n{c}"},
    "medium": {"size": 2, "prompt": "Write a question that can be answered using this passage:\n\n{c}"},
    "hard":   {"size": 3, "prompt": "Write a challenging question starting with why or how that requires understanding of this passage:\n\n{c}"},
}


def load_model():
    global _tok, _model
    with _lock:
        if _model is None:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            print(f"Loading {MODEL_NAME} ...")
            _tok = AutoTokenizer.from_pretrained(MODEL_NAME)
            _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME).eval()
            print("Model ready.")
    return _tok, _model


def _run(prompts, per=1, beams=4, max_new=48):
    """Run the model; returns one list of `per` strings for every prompt."""
    import torch
    tok, model = load_model()
    results = []
    with _lock, torch.no_grad():
        for i in range(0, len(prompts), BATCH):
            batch = prompts[i:i + BATCH]
            enc = tok(batch, return_tensors="pt", padding=True, truncation=True, max_length=512)
            out = model.generate(**enc, max_new_tokens=max_new, num_beams=max(beams, per),
                                 num_return_sequences=per, early_stopping=True)
            texts = tok.batch_decode(out, skip_special_tokens=True)
            results += [texts[j * per:(j + 1) * per] for j in range(len(batch))]
    return results


def _spread(items, limit):
    if len(items) <= limit:
        return items
    step = len(items) / limit
    return [items[int(i * step)] for i in range(limit)]


def _question_pool(text, n, difficulty):
    cfg = DIFFICULTY[difficulty]
    chunks = _spread(make_chunks(split_sentences(text), size=cfg["size"]), min(max(n * 2, 6), 20))
    per = 3 if n > 5 else 2
    cands = _run([cfg["prompt"].format(c=c) for c in chunks], per=per)
    items = []
    for rank in range(per):                      # best candidate of every chunk first
        for chunk, cs in zip(chunks, cands):
            if rank < len(cs):
                q = clean_question(cs[rank])
                if q and is_valid_question(q):
                    items.append({"question": q, "source": chunk})
    return remove_duplicates(items, key=lambda x: x["question"])


def _add_answers(items):
    prompts = [f"Answer the question in a few words using only the passage.\n\nPassage: {i['source']}\n\nQuestion: {i['question']}"
               for i in items]
    for it, r in zip(items, _run(prompts, beams=3, max_new=40)):
        it["answer"] = r[0].strip().rstrip(".")


def _true_false(text, n):
    sents = [s for s in split_sentences(text) if 6 <= len(s.split()) <= 35]
    if not sents:
        raise ValueError("No suitable sentences found for true/false questions.")
    sents = _spread(sents, min(n, len(sents)))
    make_false = [i % 2 == 1 for i in range(len(sents))]
    to_alter = [s for s, f in zip(sents, make_false) if f]
    altered = iter(_run([f"Rewrite the sentence so that it states something factually incorrect, "
                         f"changing only one key word or fact:\n\n{s}" for s in to_alter], beams=4, max_new=64)) if to_alter else iter([])
    items = []
    for s, f in zip(sents, make_false):
        fake = next(altered)[0].strip() if f else ""
        if f and fake and fake.lower() != s.lower() and overlap(fake, s) >= 0.5:
            items.append({"type": "tf", "question": fake, "answer": "False", "explanation": s, "source": s})
        else:
            items.append({"type": "tf", "question": s, "answer": "True", "explanation": s, "source": s})
    random.Random(len(text)).shuffle(items)
    return items


def generate(text: str, n: int = 5, qtype: str = "short", difficulty: str = "medium"):
    text = clean_text(text)
    ok, msg = validate_text(text)
    if not ok:
        raise ValueError(msg)
    if not split_sentences(text):
        raise ValueError("No usable sentences found. Paste full sentences of study material.")
    if qtype == "tf":
        return _true_false(text, n)

    pool = _question_pool(text, n, difficulty)[:n + 4]   # a few extras to filter from
    if not pool:
        return []
    _add_answers(pool)
    for it in pool:
        it["score"] = quality_score(it["question"], it["source"], it["answer"])
    good = [i for i in pool if i["answer"] and i["score"] >= 35] or [i for i in pool if i["answer"]]
    good.sort(key=lambda x: -x["score"])

    if qtype == "mcq":
        rng = random.Random(len(text))
        extra = key_terms(text)
        answers = [i["answer"] for i in good]
        mcqs = []
        for it in good:
            built = make_options(it["answer"], it["question"], answers + extra, rng)
            if built:
                it["options"], it["correct_index"] = built
                mcqs.append(it)
        good = mcqs
    for it in good:
        it["type"] = qtype
    return good[:n]
