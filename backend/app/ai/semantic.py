from difflib import SequenceMatcher
from typing import Tuple


def _token_set(text: str):
    if not text:
        return set()
    toks = [t.strip().lower() for t in text.split() if t.strip()]
    return set(toks)


def jaccard_score(a: str, b: str) -> float:
    sa = _token_set(a)
    sb = _token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = sa.intersection(sb)
    union = sa.union(sb)
    return len(inter) / len(union)


def sequence_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio()


def combined_similarity(a: str, b: str) -> float:
    """Combined similarity metric (0..1) using sequence ratio and token Jaccard."""
    s1 = sequence_ratio(a, b)
    s2 = jaccard_score(a, b)
    return (s1 + s2) / 2.0


def short_diff_summary(a: str, b: str, max_chars: int = 200) -> str:
    """Return a terse diff-like summary (first changed excerpt).

    Uses simple heuristics to produce a compact explanation for UI.
    """
    if a == b:
        return "no textual differences detected"

    # Find a short region where they differ
    matcher = SequenceMatcher(None, a or "", b or "")
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            excerpt_a = (a or "")[max(0, i1 - 20): i2 + 20]
            excerpt_b = (b or "")[max(0, j1 - 20): j2 + 20]
            return f"A: {excerpt_a[:max_chars]}\nB: {excerpt_b[:max_chars]}"
    return "text differs"
