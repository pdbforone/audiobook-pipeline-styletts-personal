"""
Test resilience features: Safety Gates + ASR Validation + Llama Rewriter

Tests the complete integration of:
1. Safety gates (PolicyEngine)
2. ASR validation (Whisper)
3. Llama rewriter with ASR feedback
"""

import pytest
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSafetyGates:
    """Test safety gate integration."""

    def test_safety_gates_import(self):
        """Verify safety gates module imports correctly."""
        from policy_engine.safety_gates import SafetyGates

        gates = SafetyGates()
        assert gates is not None
        assert gates.min_runs_for_autonomy == 5
        assert gates.max_failure_rate == 0.35

    def test_safety_check_insufficient_data(self):
        """Test safety gates block autonomy with insufficient runs."""
        from policy_engine.safety_gates import SafetyGates

        gates = SafetyGates()
        run_summary = {
            "total_runs": 3,  # Less than min_runs_for_autonomy (5)
            "failed_runs": 0
        }

        result = gates.check_gates(run_summary)

        assert result["allow_autonomy"] is False
        assert "insufficient_data" in result["blocked_reasons"]
        assert result["downgrade_to_supervised"] is True

    def test_safety_check_high_failure_rate(self):
        """Test safety gates block autonomy with high failure rate."""
        from policy_engine.safety_gates import SafetyGates

        gates = SafetyGates()
        run_summary = {
            "total_runs": 10,
            "failed_runs": 4  # 40% failure rate > 35% threshold
        }

        result = gates.check_gates(run_summary)

        assert result["allow_autonomy"] is False
        assert "high_failure_rate" in result["blocked_reasons"]

    def test_safety_check_pass(self):
        """Test safety gates allow autonomy when conditions met."""
        from policy_engine.safety_gates import SafetyGates

        gates = SafetyGates()
        run_summary = {
            "total_runs": 10,
            "failed_runs": 2,  # 20% failure rate < 35%
            "recent_performance": {"avg_rtf": 3.0},
            "historical_performance": {"avg_rtf": 3.0}
        }

        result = gates.check_gates(run_summary, learning_mode="enforce")

        assert result["allow_autonomy"] is True
        assert len(result["blocked_reasons"]) == 0

    def test_policy_engine_integration(self):
        """Test safety gates integrated into PolicyEngine."""
        from policy_engine.policy_engine import TuningOverridesStore

        store = TuningOverridesStore()

        # Verify method exists
        assert hasattr(store, 'check_safety_gates')

        run_summary = {
            "total_runs": 5,
            "failed_runs": 1
        }

        result = store.check_safety_gates(run_summary)
        assert "allow_autonomy" in result
        assert "blocked_reasons" in result


class TestASRValidation:
    """Test ASR validation module."""

    def test_asr_validator_import(self):
        """Verify ASR validator imports correctly."""
        try:
            from phase4_tts.src.asr_validator import ASRValidator

            validator = ASRValidator(model_size="tiny")
            assert validator is not None
            assert validator.wer_warning_threshold == 0.20
            assert validator.wer_critical_threshold == 0.40
        except ImportError as e:
            pytest.skip(f"ASR validator not available: {e}")

    def test_asr_wer_calculation(self):
        """Test WER calculation logic."""
        try:
            from phase4_tts.src.asr_validator import ASRValidator

            validator = ASRValidator()

            # Identical text = WER 0%
            wer = validator._calculate_wer("Hello world", "Hello world")
            assert wer == 0.0

            # Completely different = high WER
            wer = validator._calculate_wer("Hello world", "Goodbye universe")
            assert wer > 0.5

        except ImportError:
            pytest.skip("ASR validator not available")

    def test_asr_recommendation_logic(self):
        """Test ASR recommendation strategy."""
        try:
            from phase4_tts.src.asr_validator import ASRValidator

            validator = ASRValidator()

            # Low WER = pass
            rec = validator._get_recommendation(0.10, [])
            assert rec == "pass"

            # Moderate WER = rewrite
            rec = validator._get_recommendation(0.25, [])
            assert rec == "rewrite"

            # Critical WER = switch engine
            rec = validator._get_recommendation(0.50, ["possible_gibberish"])
            assert rec == "switch_engine"

        except ImportError:
            pytest.skip("ASR validator not available")


class TestLlamaRewriter:
    """Test Llama rewriter with ASR feedback."""

    def test_llama_rewriter_import(self):
        """Verify Llama rewriter imports correctly."""
        try:
            from agents.llama_rewriter import LlamaRewriter

            rewriter = LlamaRewriter()
            assert rewriter is not None
            assert hasattr(rewriter, 'rewrite_from_asr_feedback')
        except ImportError as e:
            pytest.skip(f"Llama rewriter not available: {e}")

    def test_llama_rewriter_has_asr_method(self):
        """Test that ASR feedback method exists."""
        try:
            from agents.llama_rewriter import LlamaRewriter
            import inspect

            rewriter = LlamaRewriter()

            # Check method signature
            sig = inspect.signature(rewriter.rewrite_from_asr_feedback)
            params = list(sig.parameters.keys())

            assert 'original_text' in params
            assert 'asr_transcription' in params
            assert 'asr_issues' in params
            assert 'wer' in params

        except ImportError:
            pytest.skip("Llama rewriter not available")

    def test_llama_fallback_behavior(self):
        """Test Llama rewriter fallback when LLM unavailable."""
        try:
            from agents.llama_rewriter import LlamaRewriter

            # This should not crash even if Ollama is down
            rewriter = LlamaRewriter()

            result = rewriter.rewrite_from_asr_feedback(
                original_text="Test text",
                asr_transcription="Test text",
                asr_issues=["high_wer"],
                wer=0.3
            )

            # Should have fallback structure
            assert "rewritten" in result
            assert "notes" in result
            assert "confidence" in result
            assert "strategy" in result

        except ImportError:
            pytest.skip("Llama rewriter not available")


class TestPhase4Integration:
    """Test Phase 4 integration of ASR + Llama."""

    def test_phase4_imports_asr(self):
        """Verify Phase 4 imports ASR validator."""
        try:
            import phase4_tts.src.main_multi_engine as phase4

            # Should have ASRValidator imported (or None if not available)
            assert hasattr(phase4, 'ASRValidator')

        except ImportError as e:
            pytest.skip(f"Phase 4 module not available: {e}")

    def test_phase4_imports_llama(self):
        """Verify Phase 4 imports Llama rewriter."""
        try:
            import phase4_tts.src.main_multi_engine as phase4

            # Should have LlamaRewriter imported (or None if not available)
            assert hasattr(phase4, 'LlamaRewriter')

        except ImportError as e:
            pytest.skip(f"Phase 4 module not available: {e}")


class TestDocumentation:
    """Test that documentation files exist."""

    def test_resilience_features_doc_exists(self):
        """Verify resilience features documentation exists."""
        doc_path = Path(__file__).parent.parent / "RESILIENCE_FEATURES.md"
        assert doc_path.exists(), "RESILIENCE_FEATURES.md should exist"

    def test_asr_llama_doc_exists(self):
        """Verify ASR+Llama integration documentation exists."""
        doc_path = Path(__file__).parent.parent / "ASR_LLAMA_INTEGRATION.md"
        assert doc_path.exists(), "ASR_LLAMA_INTEGRATION.md should exist"

    def test_roadmap_updated(self):
        """Verify roadmap mentions resilience features."""
        roadmap = Path(__file__).parent.parent / "AUTONOMOUS_PIPELINE_ROADMAP.md"
        assert roadmap.exists()

        content = roadmap.read_text(encoding='utf-8')
        assert "Safety Gates" in content
        assert "ASR Validation" in content
        assert "2025-11-27" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
