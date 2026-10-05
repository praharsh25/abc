"""Question cleaning, duplicate removal, quality scoring and MCQ options."""
import re
from difflib import SequenceMatcher

from text_preprocessing import STOPWORDS

QUESTION_START = re.compile(r"(?i)^(what|who|whom|whose|when|where|which|why|how|name|explain|describe|define|state|list|is|are|does|do|did|can|in)\b")


def clean_question(q: str) -> str:
    q = re.sub(r"\s+", " ", q).strip()
    q = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", q)
    q = re.sub(r"^(question|q)\s*\d*\s*[:.-]\s*", "", q, flags=re.I)
    if not q:
        return ""
    q = q[0].upper() + q[1:]
    return q.rstrip(" .!,;:?") + "?"


def is_valid_question(q: str) -> bool:
    return 4 <= len(q.split()) <= 40


def tokens(s: str):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOPWORDS}


def overlap(a: str, b: str) -> float:
    ta, tb = set(re.findall(r"[a-z0-9]+", a.lower())), set(re.findall(r"[a-z0-9]+", b.lower()))
    return len(ta & tb) / len(ta | tb) if ta and tb else 0.0


def is_duplicate(a: str, b: str) -> bool:
    if SequenceMatcher(None, a.lower(), b.lower()).ratio() >= 0.85:
        return True
    ta, tb = tokens(a), tokens(b)
    return bool(ta and tb) and len(ta & tb) / len(ta | tb) >= 0.7


def remove_duplicates(items, key=lambda x: x):
    unique = []
    for it in items:
        if not any(is_duplicate(key(it), key(u)) for u in unique):
            unique.append(it)
    return unique


def quality_score(question: str, source: str, answer: str) -> int:
    """0-100 heuristic: question form, grounding in the source, answerability, length."""
    qt, st, at = tokens(question), tokens(source), tokens(answer)
    s = 30 if QUESTION_START.match(question) else 0
    if qt:
        cover = len(qt & st) / len(qt)
        s += 30 * min(1.0, cover / 0.8)
        if cover > 0.95:
            s -= 10                      # nearly a copy of the source
    if at and at & st:
        s += 25                          # answer is grounded in the passage
    if 5 <= len(question.split()) <= 22:
        s += 15
    if answer and answer.lower() in question.lower():
        s -= 25                          # answer leaks into the question
    return max(0, min(100, round(s)))


def make_options(answer: str, question: str, pool, rng):
    """Return (options, correct_index) with 3 distractors, or None if not enough candidates."""
    if not answer or answer.replace(".", "").isdigit():
        return None
    a, atok, qtok, n = answer.lower(), tokens(answer), tokens(question), len(answer.split())
    seen, cands = set(), []
    for c in pool:
        cl = c.lower().strip()
        if not cl or cl in seen:
            continue
        seen.add(cl)
        ct = tokens(c)
        if (not ct or ct & atok or ct & qtok or cl in a or a in cl
                or abs(len(c.split()) - n) > 1 or len(c.split()) > 4):
            continue
        cands.append(c)
    if len(cands) < 3:
        return None
    fmt = lambda x: x[0].upper() + x[1:]
    options = [fmt(x) for x in rng.sample(cands[:15], 3)] + [fmt(answer)]
    rng.shuffle(options)
    return options, options.index(fmt(answer))
