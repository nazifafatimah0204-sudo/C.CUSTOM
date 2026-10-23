"""Lightweight RAG: split regulations into chunks, rank them with TF-IDF, return the best matches."""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def chunk_text(text: str, max_len: int = 900) -> list:
    """Split text at blank lines; cut very long blocks into smaller pieces."""
    chunks = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if len(block) < 25:
            continue
        while len(block) > max_len:
            cut = block.rfind(". ", 0, max_len)
            cut = cut + 1 if cut > 200 else max_len
            chunks.append(block[:cut].strip())
            block = block[cut:].strip()
        if block:
            chunks.append(block)
    return chunks


class KnowledgeBase:
    def __init__(self, base_text: str, extra_texts=None):
        texts = [base_text] + list(extra_texts or [])
        self.chunks = []
        for t in texts:
            self.chunks.extend(chunk_text(t))
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(self.chunks) if self.chunks else None

    def search(self, query: str, k: int = 3) -> list:
        if self.matrix is None or not query.strip():
            return []
        scores = linear_kernel(self.vectorizer.transform([query]), self.matrix).ravel()
        best = scores.argsort()[::-1][:k]
        return [(float(scores[i]), self.chunks[i]) for i in best if scores[i] > 0]
