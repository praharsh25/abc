"""Text cleaning, validation, sentence splitting, chunking and key-term extraction."""
import re
from collections import Counter

MIN_WORDS, MAX_WORDS = 15, 3000
STOPWORDS = set("""a an the is are was were be been being of in on at to and or but by for with as that this these those
it its from into than then so such which who whom whose what when where why how their there they them his her he she we you
i not no can could may might will would shall should do does did has have had also more most other some any each both
about over under between through during while after before because however thus""".split())


def clean_text(text: str) -> str:
    text = re.sub(r"\s*\[\d+\]", "", text)               # citation markers like [1]
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", " ", text)    # control characters
    return re.sub(r"\s+", " ", text).strip()


def validate_text(text: str):
    n = len(text.split())
    if n < MIN_WORDS:
        return False, f"Add more text: at least {MIN_WORDS} words are needed (you have {n})."
    if n > MAX_WORDS:
        return False, f"Shorten the text: the limit is {MAX_WORDS} words (you have {n})."
    return True, ""


def split_sentences(text: str):
    sentences = None
    try:
        import nltk
        try:
            sentences = nltk.sent_tokenize(text)
        except LookupError:
            for pkg in ("punkt_tab", "punkt"):
                nltk.download(pkg, quiet=True)
            sentences = nltk.sent_tokenize(text)
    except Exception:
        sentences = None
    if not sentences:  # regex fallback if NLTK or its data is unavailable
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [s.strip() for s in sentences if len(s.split()) >= 3]


def make_chunks(sentences, size=2, stride=1):
    """Sliding windows of `size` sentences so each prompt has context."""
    if len(sentences) <= size:
        return [" ".join(sentences)] if sentences else []
    return [" ".join(sentences[i:i + size]) for i in range(0, len(sentences) - size + 1, stride)]


def key_terms(text: str, limit: int = 60):
    """Frequent single words and word pairs, used as MCQ distractor candidates."""
    low = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]+", text)]
    ok = lambda w: len(w) >= 4 and w not in STOPWORDS
    uni = [w for w, _ in Counter(w for w in low if ok(w)).most_common(limit)]
    bi = [f"{a} {b}" for a, b in zip(low, low[1:]) if ok(a) and ok(b)]
    return uni + [w for w, _ in Counter(bi).most_common(limit)]
