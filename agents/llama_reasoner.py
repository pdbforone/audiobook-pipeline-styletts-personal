"""
Llama Reasoner Agent - Pipeline failure analysis and fix suggestions.

This agent analyzes pipeline failures to:
- Identify root causes from logs
- Suggest concrete fixes
- Propose configuration changes
- Generate patch suggestions (never auto-applied)

Usage:
    from agents import LlamaReasoner

    reasoner = LlamaReasoner()
    analysis = reasoner.analyze_failure(log_content, chunk_data)
    print(analysis.root_cause)
    print(analysis.suggested_fix)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .llama_base import LlamaAgent, DEFAULT_MODEL

logger = logging.getLogger(__name__)

REASONER_SYSTEM_PROMPT = """You are a pipeline debugging expert for an audiobook TTS system.

The system has these phases:
- Phase 1: Validation (PDF/EPUB repair)
- Phase 2: Text extraction
- Phase 3: Semantic chunking
- Phase 4: TTS synthesis (XTTS, Kokoro, Piper engines)
- Phase 5: Audio enhancement and mastering
- Phase 6: Orchestration

Common failure patterns:
- OOM: Out of memory during TTS synthesis
- Timeout: Chunk took too long to synthesize
- Truncation: Text too long for engine
- Audio quality: Silence, artifacts, or wrong duration
- Pydantic: Schema validation errors
- File I/O: Missing files, permission issues

Your job is to:
1. Identify the root cause of failures
2. Suggest specific, actionable fixes
3. Recommend configuration changes
4. Provide prevention strategies

Always be specific and actionable. Never suggest vague solutions."""


@dataclass
class FailureAnalysis:
    """Result of failure analysis."""

    root_cause: str
    category: str  # oom, timeout, truncation, quality, schema, io, unknown
    confidence: float  # 0.0 to 1.0
    suggested_fix: str
    config_changes: Dict[str, Any] = field(default_factory=dict)
    prevention_strategy: str = ""
    affected_components: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class PatchSuggestion:
    """A suggested code or config patch."""

    target: str  # File or config to modify
    description: str
    diff: str  # Suggested change
    confidence: float
    reasoning: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending_review"  # Never auto-applied


class LlamaReasoner:
    """
    LLM-powered pipeline failure analyzer.

    Analyzes logs and chunk data to identify root causes
    and suggest fixes. All suggestions require human approval.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        agent: Optional[LlamaAgent] = None,
    ):
        self.agent = agent or LlamaAgent(model=model)

    def analyze_failure(
        self,
        log_content: str,
        chunk_data: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureAnalysis:
        """
        Analyze a pipeline failure.

        Args:
            log_content: Relevant log output (last ~100 lines)
            chunk_data: Optional chunk metadata from pipeline.json
            context: Optional additional context (phase, file_id, etc.)

        Returns:
            FailureAnalysis with root cause and suggestions
        """
        # Truncate log to avoid token limits
        log_excerpt = log_content[-3000:] if len(log_content) > 3000 else log_content

        prompt = f"""Analyze this TTS pipeline failure:

LOG OUTPUT:
{log_excerpt}

{f"CHUNK DATA: {json.dumps(chunk_data, indent=2)}" if chunk_data else ""}
{f"CONTEXT: {json.dumps(context, indent=2)}" if context else ""}

Analyze and respond with JSON:
{{
    "root_cause": "<specific cause>",
    "category": "<oom|timeout|truncation|quality|schema|io|unknown>",
    "confidence": <0.0-1.0>,
    "suggested_fix": "<specific action to take>",
    "config_changes": {{"key": "value"}},
    "prevention_strategy": "<how to prevent recurrence>",
    "affected_components": ["<phase or module>"],
    "severity": "<low|medium|high|critical>"
}}"""

        response = self.agent.query_json(
            prompt,
            max_tokens=800,
            system_prompt=REASONER_SYSTEM_PROMPT,
        )

        if "error" in response:
            # Fallback to pattern matching
            return self._pattern_based_analysis(log_content, chunk_data)

        return FailureAnalysis(
            root_cause=response.get("root_cause", "Unknown failure"),
            category=response.get("category", "unknown"),
            confidence=float(response.get("confidence", 0.5)),
            suggested_fix=response.get("suggested_fix", "Review logs manually"),
            config_changes=response.get("config_changes", {}),
            prevention_strategy=response.get("prevention_strategy", ""),
            affected_components=response.get("affected_components", []),
            severity=response.get("severity", "medium"),
        )

    def _pattern_based_analysis(
        self,
        log_content: str,
        chunk_data: Optional[Dict[str, Any]] = None,
    ) -> FailureAnalysis:
        """Fallback pattern-based analysis when LLM unavailable."""
        log_lower = log_content.lower()

        # OOM patterns
        if any(p in log_lower for p in ["out of memory", "memoryerror", "cuda oom", "killed"]):
            return FailureAnalysis(
                root_cause="Out of memory during processing",
                category="oom",
                confidence=0.8,
                suggested_fix="Reduce worker count or switch to lighter engine (Kokoro/Piper)",
                config_changes={"workers": 1, "engine": "kokoro"},
                prevention_strategy="Enable cpu_safe mode or reduce chunk sizes",
                affected_components=["phase4_tts"],
                severity="high",
            )

        # Timeout patterns
        if any(p in log_lower for p in ["timeout", "timed out", "exceeded", "too slow"]):
            return FailureAnalysis(
                root_cause="Processing timeout",
                category="timeout",
                confidence=0.7,
                suggested_fix="Increase timeout or use faster engine",
                config_changes={"rtf_fallback_threshold": 3.0, "enable_latency_fallback": True},
                prevention_strategy="Enable automatic fallback to Kokoro for slow chunks",
                affected_components=["phase4_tts"],
                severity="medium",
            )

        # Truncation patterns
        if any(p in log_lower for p in ["truncat", "text too long", "max", "exceeded limit"]):
            text_len = chunk_data.get("text_len", 0) if chunk_data else 0
            return FailureAnalysis(
                root_cause=f"Text too long for engine ({text_len} chars)",
                category="truncation",
                confidence=0.8,
                suggested_fix="Reduce chunk size or enable text splitting",
                config_changes={"split_char_limit": 1000, "enable_splitting": True},
                prevention_strategy="Use registry-based limits per engine",
                affected_components=["phase3_chunking", "phase4_tts"],
                severity="medium",
            )

        # Quality patterns
        if any(p in log_lower for p in ["silence", "no audio", "corrupt", "invalid", "empty"]):
            return FailureAnalysis(
                root_cause="Audio quality issue - silence or corruption",
                category="quality",
                confidence=0.6,
                suggested_fix="Retry with different engine or check input text",
                config_changes={},
                prevention_strategy="Enable tier1 validation with stricter thresholds",
                affected_components=["phase4_tts", "phase5_enhancement"],
                severity="medium",
            )

        # Schema/validation patterns
        if any(p in log_lower for p in ["pydantic", "validationerror", "schema", "missing key"]):
            return FailureAnalysis(
                root_cause="Schema validation failure",
                category="schema",
                confidence=0.7,
                suggested_fix="Check pipeline.json structure matches expected schema",
                config_changes={},
                prevention_strategy="Validate pipeline.json before each phase",
                affected_components=["pipeline_common"],
                severity="high",
            )

        # I/O patterns (file system, permissions, disk)
        if any(p in log_lower for p in [
            "filenotfounderror", "permissionerror", "no such file",
            "cannot open", "disk full", "ioerror", "permission denied"
        ]):
            return FailureAnalysis(
                root_cause="File system or I/O error",
                category="io",
                confidence=0.8,
                suggested_fix="Check file paths, permissions, and available disk space",
                config_changes={},
                prevention_strategy="Validate paths and disk space before processing",
                affected_components=["phase1_validation", "phase4_tts", "phase5_enhancement"],
                severity="high",
            )

        # Default unknown
        return FailureAnalysis(
            root_cause="Unknown failure - manual review needed",
            category="unknown",
            confidence=0.3,
            suggested_fix="Review full logs and chunk data manually",
            config_changes={},
            prevention_strategy="Add more detailed logging",
            affected_components=[],
            severity="medium",
        )

    def suggest_patch(
        self,
        analysis: FailureAnalysis,
        target_file: Optional[str] = None,
    ) -> PatchSuggestion:
        """
        Generate a patch suggestion based on failure analysis.

        IMPORTANT: Patches are NEVER auto-applied.
        They go to .pipeline/staged_patches/ for human review.
        """
        prompt = f"""Based on this failure analysis, suggest a code or config patch:

ROOT CAUSE: {analysis.root_cause}
CATEGORY: {analysis.category}
SUGGESTED FIX: {analysis.suggested_fix}
CONFIG CHANGES: {json.dumps(analysis.config_changes)}
TARGET FILE: {target_file or "auto-detect"}

Generate a specific patch that fixes this issue.
Output JSON:
{{
    "target": "<file path>",
    "description": "<what this patch does>",
    "diff": "<patch content or config change>",
    "confidence": <0.0-1.0>,
    "reasoning": "<why this fix works>"
}}"""

        response = self.agent.query_json(prompt, max_tokens=600)

        if "error" in response:
            # Generate basic config patch
            return PatchSuggestion(
                target=target_file or ".pipeline/tuning_overrides.json",
                description=analysis.suggested_fix,
                diff=json.dumps(analysis.config_changes, indent=2),
                confidence=0.5,
                reasoning=f"Based on {analysis.category} failure pattern",
            )

        return PatchSuggestion(
            target=response.get("target", target_file or "unknown"),
            description=response.get("description", analysis.suggested_fix),
            diff=response.get("diff", ""),
            confidence=float(response.get("confidence", 0.5)),
            reasoning=response.get("reasoning", "LLM suggestion"),
        )

    def stage_patch(
        self,
        patch: PatchSuggestion,
        staging_dir: Path = Path(".pipeline/staged_patches"),
    ) -> Path:
        """
        Stage a patch for human review.

        Patches are NEVER auto-applied. This creates a file in
        staging_dir for human review and approval.
        """
        staging_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_target = re.sub(r'[^\w\-]', '_', patch.target)
        patch_file = staging_dir / f"{timestamp}_{safe_target}.json"

        patch_data = {
            "target": patch.target,
            "description": patch.description,
            "diff": patch.diff,
            "confidence": patch.confidence,
            "reasoning": patch.reasoning,
            "created_at": patch.created_at,
            "status": "pending_review",
            "reviewed_by": None,
            "approved": None,
        }

        patch_file.write_text(json.dumps(patch_data, indent=2))
        logger.info(f"Patch staged for review: {patch_file}")

        return patch_file

    def get_staged_patches(
        self,
        staging_dir: Path = Path(".pipeline/staged_patches"),
    ) -> List[Dict[str, Any]]:
        """Get all pending patches for review."""
        if not staging_dir.exists():
            return []

        patches = []
        for patch_file in staging_dir.glob("*.json"):
            try:
                data = json.loads(patch_file.read_text())
                data["file"] = str(patch_file)
                patches.append(data)
            except Exception as e:
                logger.warning(f"Failed to read patch {patch_file}: {e}")

        return sorted(patches, key=lambda p: p.get("created_at", ""), reverse=True)
