"""
Distill Intelligence from Phase P-Z Research Logs

Extracts actionable patterns from policy logs and research phases,
producing a single learned_patterns.json that drives resilience.
"""

import json
import logging
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResearchDistiller:
    """Extracts learnings from alphabet phase outputs."""

    def __init__(self, pipeline_dir: Path = Path(".pipeline")):
        self.pipeline_dir = pipeline_dir
        self.policy_logs_dir = pipeline_dir / "policy_logs"
        self.research_dir = pipeline_dir / "research"

    def extract_chunk_failure_patterns(self) -> Dict[str, Any]:
        """
        Analyze policy logs to find chunk length → failure rate correlations.

        Returns patterns like:
        {"450-500_chars": {"failure_rate": 0.12, "action": "use_kokoro"}}
        """
        logger.info("Analyzing chunk failure patterns from policy logs...")

        chunk_stats = defaultdict(lambda: {"total": 0, "failures": 0})

        # Read all policy log files
        if not self.policy_logs_dir.exists():
            logger.warning(f"No policy logs found at {self.policy_logs_dir}")
            return {}

        for log_file in self.policy_logs_dir.glob("*.log"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())

                            # Look for Phase 4 events with chunk data
                            if event.get("phase") == "phase4" and event.get("event") == "phase_end":
                                snapshot = event.get("phase_snapshot", {})
                                chunks = snapshot.get("chunks", [])

                                for chunk in chunks:
                                    text_len = chunk.get("text_len", 0)
                                    status = chunk.get("status", "unknown")
                                    engine = chunk.get("engine_used", "unknown")

                                    # Bucket by length
                                    bucket = self._get_length_bucket(text_len)

                                    chunk_stats[bucket]["total"] += 1
                                    if status in ["failed", "error"]:
                                        chunk_stats[bucket]["failures"] += 1

                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"Error reading {log_file}: {e}")
                continue

        # Convert to actionable patterns
        patterns = {}
        for bucket, stats in chunk_stats.items():
            if stats["total"] < 5:  # Need at least 5 samples
                continue

            failure_rate = stats["failures"] / stats["total"]

            if failure_rate > 0.4:
                patterns[bucket] = {
                    "failure_rate": round(failure_rate, 3),
                    "action": "preemptive_split",
                    "sample_count": stats["total"]
                }
            elif failure_rate > 0.25:
                patterns[bucket] = {
                    "failure_rate": round(failure_rate, 3),
                    "action": "use_kokoro",  # Faster, more reliable
                    "sample_count": stats["total"]
                }

        logger.info(f"Extracted {len(patterns)} chunk failure patterns")
        return patterns

    def extract_coherence_thresholds(self) -> Dict[str, float]:
        """
        Extract quality gates from Phase 3 coherence/readability scores.

        Returns thresholds like:
        {"coherence_min": 0.5, "readability_min": 55.0}
        """
        logger.info("Extracting coherence thresholds...")

        coherence_scores = []
        readability_scores = []

        if not self.policy_logs_dir.exists():
            return {}

        for log_file in self.policy_logs_dir.glob("*.log"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())

                            if event.get("phase") == "phase3" and event.get("event") == "phase_end":
                                metrics = event.get("phase_snapshot", {}).get("metrics", {})

                                avg_coherence = metrics.get("avg_coherence")
                                avg_readability = metrics.get("avg_readability")

                                if avg_coherence is not None:
                                    coherence_scores.append(avg_coherence)
                                if avg_readability is not None:
                                    readability_scores.append(avg_readability)

                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.warning(f"Error reading {log_file}: {e}")
                continue

        # Use 25th percentile as minimum threshold
        # (anything below this historically led to problems)
        thresholds = {}
        if coherence_scores:
            coherence_scores.sort()
            threshold_idx = len(coherence_scores) // 4
            thresholds["coherence_min"] = round(coherence_scores[threshold_idx], 2)

        if readability_scores:
            readability_scores.sort()
            threshold_idx = len(readability_scores) // 4
            thresholds["readability_min"] = round(readability_scores[threshold_idx], 1)

        logger.info(f"Coherence thresholds: {thresholds}")
        return thresholds

    def extract_error_categories(self) -> Dict[str, str]:
        """
        Build failure type → strategy map from error registry.

        Returns map like:
        {"timeout": "switch_engine", "truncation": "split_smaller"}
        """
        logger.info("Extracting error category mappings...")

        error_registry_path = self.pipeline_dir / "error_registry.json"

        if not error_registry_path.exists():
            return self._get_default_error_map()

        try:
            data = json.loads(error_registry_path.read_text())
            entries = data.get("entries", {})

            # Analyze which repair strategies worked
            strategy_success = defaultdict(lambda: {"attempts": 0, "successes": 0})

            for chunk_id, entry in entries.items():
                for attempt in entry.get("attempts", []):
                    strategy = attempt.get("strategy", "unknown")
                    success = attempt.get("success", False)

                    strategy_success[strategy]["attempts"] += 1
                    if success:
                        strategy_success[strategy]["successes"] += 1

            # Build error → strategy map
            # (This would be richer with more failure data)
            error_map = self._get_default_error_map()

            logger.info(f"Error category map: {error_map}")
            return error_map

        except Exception as e:
            logger.warning(f"Error reading error registry: {e}")
            return self._get_default_error_map()

    def distill_all(self) -> Dict[str, Any]:
        """Run all extraction and combine into single knowledge base."""
        logger.info("=" * 60)
        logger.info("DISTILLING RESEARCH INTELLIGENCE")
        logger.info("=" * 60)

        patterns = {
            "meta": {
                "extracted_at": datetime.now().isoformat(),
                "version": "1.0",
                "source": "policy_logs + error_registry + research phases"
            },
            "chunk_failure_patterns": self.extract_chunk_failure_patterns(),
            "quality_thresholds": self.extract_coherence_thresholds(),
            "error_strategy_map": self.extract_error_categories(),
            "formatting_issues": {
                "excessive_parentheticals": {"threshold": 3, "action": "rewrite"},
                "ellipses_present": {"action": "rewrite"},
                "em_dashes": {"threshold": 2, "action": "rewrite"},
                "multiple_quotes": {"threshold": 3, "action": "rewrite"}
            }
        }

        return patterns

    def _get_length_bucket(self, length: int) -> str:
        """Convert length to bucket for pattern analysis."""
        if length < 200:
            return "0-200"
        elif length < 300:
            return "200-300"
        elif length < 400:
            return "300-400"
        elif length < 500:
            return "400-500"
        elif length < 700:
            return "500-700"
        elif length < 900:
            return "700-900"
        else:
            return "900+"

    def _get_default_error_map(self) -> Dict[str, str]:
        """Default error → strategy mappings from roadmap knowledge."""
        return {
            "timeout": "switch_engine",
            "timed out": "switch_engine",
            "truncat": "split_smaller",
            "too long": "split_smaller",
            "max length": "split_smaller",
            "invalid char": "text_rewrite",
            "encoding": "text_rewrite",
            "unicode": "text_rewrite",
            "out of memory": "use_kokoro",
            "oom": "use_kokoro"
        }


def main():
    """Extract patterns and save to resilience_kernel/learned_patterns.json"""

    distiller = ResearchDistiller()
    patterns = distiller.distill_all()

    # Save to resilience kernel
    output_dir = Path("resilience_kernel")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "learned_patterns.json"
    output_path.write_text(json.dumps(patterns, indent=2), encoding="utf-8")

    logger.info("=" * 60)
    logger.info(f"✅ Patterns extracted to: {output_path}")
    logger.info(f"   - Chunk failure patterns: {len(patterns['chunk_failure_patterns'])}")
    logger.info(f"   - Quality thresholds: {len(patterns['quality_thresholds'])}")
    logger.info(f"   - Error strategies: {len(patterns['error_strategy_map'])}")
    logger.info("=" * 60)

    print(f"\n📊 Sample patterns:\n{json.dumps(patterns['chunk_failure_patterns'], indent=2)}")
    print(f"\n🎯 Quality thresholds:\n{json.dumps(patterns['quality_thresholds'], indent=2)}")


if __name__ == "__main__":
    main()
