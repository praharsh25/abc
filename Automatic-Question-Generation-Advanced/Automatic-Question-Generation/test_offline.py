"""Quick tests for the non-model logic (no download needed): python test_offline.py"""
from text_preprocessing import clean_text, make_chunks, split_sentences, validate_text
from utils import clean_question, remove_duplicates

assert clean_question("1. what is photosynthesis") == "What is photosynthesis?"
assert clean_question("Q2: define   osmosis.") == "Define osmosis?"
qs = ["What does chlorophyll absorb?", "What does chlorophyll absorb ?", "Where is glucose produced?"]
assert len(remove_duplicates([clean_question(q) for q in qs])) == 2
assert validate_text("too short")[0] is False
text = clean_text("Plants make their own food [1]. Chlorophyll absorbs sunlight. Glucose and oxygen are produced.  Water is needed too.")
s = split_sentences(text)
assert len(s) == 4 and "[1]" not in text
assert len(make_chunks(s)) == 3
print("All offline tests passed.")
