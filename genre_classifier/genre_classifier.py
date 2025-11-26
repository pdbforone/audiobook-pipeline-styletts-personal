"""
Lightweight genre classifier with heuristic scoring and optional Llama refinement.
"""

from __future__ import annotations

import re
from typing import Dict

try:
    from agents import LlamaAgent
except Exception:
    LlamaAgent = None  # type: ignore


KEYWORDS = {
    "philosophy": ["philosophy", "reason", "virtue", "ethics", "logic", "metaphysics", "stoic", "plato", "aristotle"],
    "theology": ["god", "christ", "church", "scripture", "theology", "faith", "sin", "atonement"],
    "fiction": ["chapter", "story", "novel", "character", "dialogue", "narrator"],
    "history": ["war", "empire", "king", "revolution", "chronicle", "dynasty"],
    "science": ["experiment", "theory", "physics", "biology", "chemistry", "data"],
}


def _heuristic_scores(text: str) -> Dict[str, float]:
    text_lower = text.lower()
    scores: Dict[str, float] = {}
    for genre, words in KEYWORDS.items():
        count = sum(len(re.findall(rf"\\b{re.escape(w)}\\b", text_lower)) for w in words)
        scores[genre] = count
    total = sum(scores.values()) or 1.0
    return {k: v / total for k, v in scores.items()}


def classify_text(text: str, use_llama: bool = False) -> Dict[str, float]:
    """
    Returns genre labels with confidence scores.
    Example:
    { "philosophy": 0.72, "fiction": 0.21, "theology": 0.07 }
    """
    heuristic = _heuristic_scores(text)

    if not use_llama or not LlamaAgent:
        return heuristic

    try:
        agent = LlamaAgent()
        prompt = (
            "Classify the dominant genres in the following text. "
            "Return JSON mapping genre -> confidence (0-1). "
            "Keep to at most 5 genres.\n\n"
            f"Text sample:\n{text[:5000]}"
        )
        response = agent.query_json(prompt, max_tokens=200, temperature=0.2)
        if isinstance(response, dict) and response:
            return response
    except Exception:
        pass

    return heuristic
