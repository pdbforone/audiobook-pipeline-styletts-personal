"""
Rewrite policy helpers (opt-in). Does not modify the existing rewriter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class RewritePolicy:
    name: str
    description: str

    def apply(self, text: str) -> Dict[str, object]:
        raise NotImplementedError


class MinimalFixPolicy(RewritePolicy):
    def apply(self, text: str) -> Dict[str, object]:
        return {
            "policy": self.name,
            "result": text,
            "notes": "Minimal edits; prefer stability.",
            "confidence": 0.6,
        }


class TTSStabilityPolicy(RewritePolicy):
    def apply(self, text: str) -> Dict[str, object]:
        cleaned = text.replace("...", ".").strip()
        return {
            "policy": self.name,
            "result": cleaned,
            "notes": "Normalize punctuation for TTS stability.",
            "confidence": 0.7,
        }


class SemanticPreservePolicy(RewritePolicy):
    def apply(self, text: str) -> Dict[str, object]:
        return {
            "policy": self.name,
            "result": text,
            "notes": "Preserve semantics; avoid aggressive rewrites.",
            "confidence": 0.8,
        }


class StyleStrictPolicy(RewritePolicy):
    def apply(self, text: str) -> Dict[str, object]:
        tightened = " ".join(text.split())
        return {
            "policy": self.name,
            "result": tightened,
            "notes": "Strict style: condensed spacing.",
            "confidence": 0.65,
        }


class StyleRelaxedPolicy(RewritePolicy):
    def apply(self, text: str) -> Dict[str, object]:
        relaxed = text
        return {
            "policy": self.name,
            "result": relaxed,
            "notes": "Relaxed style: leave text unchanged.",
            "confidence": 0.5,
        }


POLICY_MAP = {
    "minimal_fix": MinimalFixPolicy("minimal_fix", "Minimal edits; stability first"),
    "tts_stability": TTSStabilityPolicy("tts_stability", "Normalize punctuation for TTS stability"),
    "semantic_preserve": SemanticPreservePolicy("semantic_preserve", "Preserve meaning; avoid aggressive changes"),
    "style_strict": StyleStrictPolicy("style_strict", "Tighten spacing and formatting"),
    "style_relaxed": StyleRelaxedPolicy("style_relaxed", "Leave style relaxed and close to source"),
}


def apply_policy(policy_name: str, text: str, llama_agent=None) -> Dict[str, object]:
    """
    Apply a rewrite policy; optional Llama agent may adjust notes/confidence in the future.
    """
    policy = POLICY_MAP.get(policy_name, POLICY_MAP["minimal_fix"])
    result = policy.apply(text)
    if llama_agent:
        # Placeholder for future Llama-based enrichment
        result["notes"] += " | Llama validation skipped (opt-in only)."
    return result
