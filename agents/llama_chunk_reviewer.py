"""
LlamaChunkReviewer - Post-synthesis chunk quality analysis.

Reviews synthesized chunks after Phase 4 to identify quality issues:
- Patterns in validation failures across chunks
- Text characteristics that correlate with failures
- Quality trends and anomalies
- Recommendations for re-synthesis or parameter adjustments
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent

logger = logging.getLogger(__name__)


class LlamaChunkReviewer(LlamaAgent):
    """
    Reviews chunk synthesis results to identify quality patterns and issues.

    Analyzes batch results to find:
    - Systemic issues (e.g., all long chunks fail)
    - Text patterns that correlate with failures
    - Engine-specific problems
    - Recommendations for improvement
    """

    def review_batch_results(
        self,
        chunk_results: List[Dict[str, Any]],
        file_id: str,
        engine_used: str,
    ) -> Dict[str, Any]:
        """
        Review a batch of chunk synthesis results.

        Args:
            chunk_results: List of ChunkResult dicts with:
                - chunk_id, success, text_len, audio_duration,
                - validation_tier, validation_reason, error
            file_id: File identifier
            engine_used: Primary TTS engine used

        Returns:
            dict with keys:
                - quality_score: Overall quality (0.0-1.0)
                - issues: List of identified issues
                - patterns: Detected failure patterns
                - recommendations: Suggested fixes
                - problem_chunks: Chunks needing attention
        """
        fallback = {
            "quality_score": 0.0,
            "issues": [],
            "patterns": [],
            "recommendations": [],
            "problem_chunks": [],
            "notes": "Analysis unavailable",
        }

        if not chunk_results:
            fallback["notes"] = "No chunks to analyze"
            return fallback

        # Pre-compute statistics for prompt
        stats = self._compute_batch_stats(chunk_results)

        # Build condensed chunk summary for LLM
        chunk_summary = self._build_chunk_summary(chunk_results)

        prompt = (
            "You are a TTS quality analyst. Review these synthesis results and identify issues.\n\n"
            f"**File:** {file_id}\n"
            f"**Engine:** {engine_used}\n\n"
            f"**Batch Statistics:**\n{stats}\n\n"
            f"**Chunk Results (failures highlighted):**\n{chunk_summary}\n\n"
            "**Your Analysis:**\n"
            "1. Identify patterns in failures (e.g., all long texts fail, specific validation reasons)\n"
            "2. Assess overall quality and reliability\n"
            "3. Recommend specific fixes for problem chunks\n"
            "4. Suggest parameter adjustments if needed\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "quality_score": 0.0-1.0,\n'
            '  "issues": ["issue1", "issue2"],\n'
            '  "patterns": [{"pattern": "description", "affected_chunks": ["id1", "id2"]}],\n'
            '  "recommendations": ["rec1", "rec2"],\n'
            '  "problem_chunks": [{"chunk_id": "xxx", "issue": "why", "suggested_action": "what"}],\n'
            '  "notes": "summary"\n'
            "}"
        )

        try:
            response = self.query_json(prompt, max_tokens=600, temperature=0.2)
        except Exception as exc:
            logger.warning("LlamaChunkReviewer query failed: %s", exc)
            fallback["notes"] = f"LLM error: {exc}"
            # Still return basic stats even if LLM fails
            fallback["quality_score"] = stats.get("success_rate", 0.0)
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            note = response.get("error") if isinstance(response, dict) else "Invalid response"
            fallback["notes"] = note
            fallback["quality_score"] = stats.get("success_rate", 0.0)
            return fallback

        return {
            "quality_score": float(response.get("quality_score", 0.0)),
            "issues": response.get("issues", []),
            "patterns": response.get("patterns", []),
            "recommendations": response.get("recommendations", []),
            "problem_chunks": response.get("problem_chunks", []),
            "notes": response.get("notes", ""),
            "stats": stats,
        }

    def _compute_batch_stats(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute statistics from chunk results."""
        total = len(chunk_results)
        if total == 0:
            return {"total": 0, "success_rate": 0.0}

        succeeded = sum(1 for r in chunk_results if r.get("success", False))
        failed = total - succeeded

        # Analyze failure reasons
        failure_reasons = {}
        for r in chunk_results:
            if not r.get("success", False):
                reason = r.get("validation_reason") or r.get("error") or "unknown"
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        # Text length distribution
        text_lens = [r.get("text_len", 0) for r in chunk_results]
        failed_text_lens = [r.get("text_len", 0) for r in chunk_results if not r.get("success", False)]

        avg_len = sum(text_lens) / len(text_lens) if text_lens else 0
        avg_failed_len = sum(failed_text_lens) / len(failed_text_lens) if failed_text_lens else 0

        return {
            "total": total,
            "succeeded": succeeded,
            "failed": failed,
            "success_rate": succeeded / total,
            "failure_reasons": failure_reasons,
            "avg_text_length": int(avg_len),
            "avg_failed_text_length": int(avg_failed_len),
            "long_chunk_failures": sum(1 for l in failed_text_lens if l > 1000),
        }

    def _build_chunk_summary(self, chunk_results: List[Dict[str, Any]], max_entries: int = 20) -> str:
        """Build condensed chunk summary for LLM prompt."""
        lines = []

        # Sort to show failures first
        sorted_results = sorted(chunk_results, key=lambda x: (x.get("success", False), x.get("chunk_id", "")))

        for r in sorted_results[:max_entries]:
            status = "✓" if r.get("success", False) else "✗"
            chunk_id = r.get("chunk_id", "unknown")
            text_len = r.get("text_len", 0)
            reason = r.get("validation_reason") or r.get("error") or ""

            if r.get("success", False):
                lines.append(f"{status} {chunk_id}: len={text_len}")
            else:
                lines.append(f"{status} {chunk_id}: len={text_len}, reason={reason}")

        if len(chunk_results) > max_entries:
            lines.append(f"... and {len(chunk_results) - max_entries} more chunks")

        return "\n".join(lines)

    def analyze_single_chunk(
        self,
        chunk_text: str,
        validation_result: Dict[str, Any],
        audio_duration: Optional[float] = None,
        expected_duration: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a single problematic chunk to diagnose issues.

        Args:
            chunk_text: The text that was synthesized
            validation_result: Validation details (tier, reason, etc.)
            audio_duration: Actual audio duration in seconds
            expected_duration: Expected duration based on text

        Returns:
            dict with diagnosis and recommendations
        """
        fallback = {
            "diagnosis": "Analysis unavailable",
            "likely_cause": "unknown",
            "recommended_action": "retry",
            "text_issues": [],
            "confidence": 0.0,
        }

        # Truncate text for prompt
        text_preview = chunk_text[:500] + "..." if len(chunk_text) > 500 else chunk_text

        duration_info = ""
        if audio_duration and expected_duration:
            ratio = audio_duration / expected_duration if expected_duration > 0 else 0
            duration_info = f"\nAudio duration: {audio_duration:.1f}s (expected: {expected_duration:.1f}s, ratio: {ratio:.2f})"

        prompt = (
            "Diagnose this TTS synthesis failure.\n\n"
            f"**Text ({len(chunk_text)} chars):**\n{text_preview}\n\n"
            f"**Validation Result:**\n{validation_result}\n"
            f"{duration_info}\n\n"
            "**Diagnose:**\n"
            "1. What likely caused this failure?\n"
            "2. Are there text characteristics causing issues?\n"
            "   - Abbreviations, numbers, punctuation\n"
            "   - Sentence structure, length\n"
            "   - Special characters, formatting\n"
            "3. What action should be taken?\n\n"
            "Respond with JSON:\n"
            "{\n"
            '  "diagnosis": "brief explanation",\n'
            '  "likely_cause": "main cause category",\n'
            '  "recommended_action": "retry" | "rewrite" | "split" | "skip",\n'
            '  "text_issues": ["issue1", "issue2"],\n'
            '  "suggested_rewrite": "optional rewritten text if rewrite recommended",\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        try:
            response = self.query_json(prompt, max_tokens=400, temperature=0.2)
        except Exception as exc:
            logger.warning("LlamaChunkReviewer single analysis failed: %s", exc)
            fallback["diagnosis"] = f"LLM error: {exc}"
            return fallback

        if not isinstance(response, dict) or response.get("error"):
            return fallback

        return {
            "diagnosis": response.get("diagnosis", ""),
            "likely_cause": response.get("likely_cause", "unknown"),
            "recommended_action": response.get("recommended_action", "retry"),
            "text_issues": response.get("text_issues", []),
            "suggested_rewrite": response.get("suggested_rewrite"),
            "confidence": float(response.get("confidence", 0.0)),
        }

    def quick_quality_check(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fast quality assessment without LLM (for real-time monitoring).

        Returns basic quality metrics and flags severe issues.
        """
        stats = self._compute_batch_stats(chunk_results)

        # Determine severity
        success_rate = stats.get("success_rate", 0.0)
        if success_rate >= 0.95:
            severity = "good"
        elif success_rate >= 0.80:
            severity = "warning"
        elif success_rate >= 0.50:
            severity = "poor"
        else:
            severity = "critical"

        # Check for specific patterns
        flags = []
        failure_reasons = stats.get("failure_reasons", {})

        if failure_reasons.get("duration_mismatch", 0) > 3:
            flags.append("Multiple duration mismatches - check speaking rate config")

        if failure_reasons.get("text_too_long", 0) > 0:
            flags.append("Text length exceeded - increase split threshold")

        if stats.get("long_chunk_failures", 0) > stats.get("failed", 0) * 0.5:
            flags.append("Long chunks failing disproportionately")

        if failure_reasons.get("high_wer", 0) > 3:
            flags.append("High word error rate - TTS pronunciation issues")

        return {
            "severity": severity,
            "success_rate": success_rate,
            "total_chunks": stats.get("total", 0),
            "failed_chunks": stats.get("failed", 0),
            "flags": flags,
            "top_failure_reasons": dict(
                sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
            ),
        }
