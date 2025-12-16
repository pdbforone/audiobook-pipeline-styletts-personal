#!/usr/bin/env python3
"""
Test to verify XTTS segment synthesis doesn't cause audio duplication or truncation.

This test was created to verify the fix for the split_sentences=False issue.
The bug: model.tts() has split_sentences=True by default, causing double-splitting
when we already pre-split text externally via _split_text_for_safe_synthesis().

Run with:
    cd phase4_tts
    python tests/test_xtts_no_duplication.py

Or with pytest:
    pytest tests/test_xtts_no_duplication.py -v
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "engines"))

import unittest
import tempfile
import os


class TestXTTSNoDuplication(unittest.TestCase):
    """Test that XTTS synthesis doesn't duplicate or truncate audio."""

    @classmethod
    def setUpClass(cls):
        """Check if XTTS is available."""
        cls.xtts_available = False
        cls.skip_reason = None

        try:
            from TTS.api import TTS
            cls.xtts_available = True
        except ImportError as e:
            cls.skip_reason = f"TTS library not installed: {e}"
            return

        # Check for reference audio
        cls.default_reference = (
            Path(__file__).parent.parent
            / "voice_references"
            / "george_mckayland_trimmed.wav"
        )
        if not cls.default_reference.exists():
            cls.skip_reason = f"Default reference audio not found: {cls.default_reference}"
            cls.xtts_available = False

    def setUp(self):
        if not self.xtts_available:
            self.skipTest(self.skip_reason)

    def test_segment_splitting_produces_segments(self):
        """Test that _split_text_for_safe_synthesis correctly splits long text."""
        from xtts_engine import XTTSEngine, XTTS_SAFE_SEGMENT_CHARS

        engine = XTTSEngine(device="cpu")

        # Long classical text (Plutarch-style) that should be split
        long_text = (
            "The soul of man, being immortal and having been born many times, "
            "and having seen both the things here and the things in Hades, "
            "and all things, there is nothing which it has not learned; "
            "so that it is no wonder if it is able to recollect virtue, "
            "and other things, which it knew before. "
            "For since all nature is akin, and the soul has learned all things, "
            "nothing prevents one who has recalled one thing only—"
            "which men call learning—from discovering all the rest."
        )

        segments = engine._split_text_for_safe_synthesis(long_text)

        # Should produce multiple segments
        self.assertGreater(len(segments), 1,
            f"Long text ({len(long_text)} chars) should be split into multiple segments")

        # Each segment should be under the limit
        for i, seg in enumerate(segments):
            self.assertLessEqual(len(seg), XTTS_SAFE_SEGMENT_CHARS + 60,  # Some tolerance
                f"Segment {i} too long: {len(seg)} chars")

        # Combined segments should preserve all content (approximately)
        combined = " ".join(segments)
        # Allow for minor differences due to normalization
        self.assertGreater(len(combined), len(long_text) * 0.9,
            "Splitting should preserve most content")

    def test_short_text_not_split(self):
        """Test that short text isn't unnecessarily split."""
        from xtts_engine import XTTSEngine, XTTS_SAFE_SEGMENT_CHARS

        engine = XTTSEngine(device="cpu")

        short_text = "This is a simple, short sentence for testing."

        segments = engine._split_text_for_safe_synthesis(short_text)

        self.assertEqual(len(segments), 1,
            "Short text should not be split")
        self.assertEqual(segments[0], short_text.strip())

    def test_long_sentence_clause_split(self):
        """Test that long sentences are split at clause boundaries."""
        from xtts_engine import XTTSEngine

        engine = XTTSEngine(device="cpu")

        # Very long sentence with multiple clauses
        long_sentence = (
            "When considering the nature of virtue, "
            "which the ancients debated extensively, "
            "one must recognize that wisdom comes not from mere accumulation of knowledge; "
            "rather, it emerges through careful reflection upon experience, "
            "combined with the guidance of those who have walked the path before us, "
            "and tempered by the humility to acknowledge our own limitations."
        )

        segments = engine._split_long_sentence(long_sentence, max_chars=220)

        # Should produce multiple segments
        self.assertGreater(len(segments), 1,
            f"Long sentence ({len(long_sentence)} chars) should be split")

        # Each segment should be reasonable length
        for i, seg in enumerate(segments):
            self.assertLessEqual(len(seg), 280,  # Hard max with tolerance
                f"Segment {i} exceeds limit: {len(seg)} chars: {seg[:50]}...")

    @unittest.skipUnless(
        os.environ.get("RUN_XTTS_SYNTHESIS_TEST", "0") == "1",
        "Set RUN_XTTS_SYNTHESIS_TEST=1 to run actual synthesis test"
    )
    def test_synthesis_no_duplication(self):
        """
        Test actual synthesis doesn't produce duplicated audio.

        This is a heavy test that loads the XTTS model.
        Run with: RUN_XTTS_SYNTHESIS_TEST=1 pytest tests/test_xtts_no_duplication.py::TestXTTSNoDuplication::test_synthesis_no_duplication -v
        """
        import numpy as np
        import soundfile as sf
        from xtts_engine import XTTSEngine

        engine = XTTSEngine(device="cpu")
        engine.load_model()

        # Test text that would trigger duplication with the old bug
        test_text = (
            "Philosophy teaches us that wisdom begins with acknowledging our ignorance. "
            "The ancient Greeks understood this well, and Socrates made it the foundation "
            "of his method of inquiry."
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Synthesize
            audio = engine.synthesize(
                text=test_text,
                reference_audio=self.default_reference,
                language="en",
            )

            # Save for inspection
            output_path = Path(tmpdir) / "test_output.wav"
            sf.write(output_path, audio, engine.get_sample_rate())

            # Basic validation: audio should be reasonable length
            expected_duration = len(test_text) / 15  # ~15 chars/second rough estimate
            actual_duration = len(audio) / engine.get_sample_rate()

            # Check duration is reasonable (not doubled from duplication)
            self.assertLess(actual_duration, expected_duration * 2,
                f"Audio duration ({actual_duration:.1f}s) seems too long for text length, "
                f"may indicate duplication")

            # Check duration isn't too short (truncation)
            self.assertGreater(actual_duration, expected_duration * 0.3,
                f"Audio duration ({actual_duration:.1f}s) seems too short, "
                f"may indicate truncation")

            print(f"\nSynthesis test passed:")
            print(f"  Text length: {len(test_text)} chars")
            print(f"  Expected duration: ~{expected_duration:.1f}s")
            print(f"  Actual duration: {actual_duration:.1f}s")
            print(f"  Output: {output_path}")


class TestModelTTSParameters(unittest.TestCase):
    """Test that model.tts() is called with correct parameters."""

    def test_split_sentences_false_in_code(self):
        """Verify split_sentences=False is present in the code."""
        from pathlib import Path

        xtts_engine_path = Path(__file__).parent.parent / "engines" / "xtts_engine.py"
        content = xtts_engine_path.read_text()

        # Count occurrences of split_sentences=False
        count = content.count("split_sentences=False")

        self.assertGreaterEqual(count, 2,
            f"Expected at least 2 occurrences of split_sentences=False, found {count}. "
            "Both model.tts() calls should have this parameter to prevent double-splitting.")

        # Also verify enable_text_splitting=False for inference path
        inference_count = content.count("enable_text_splitting=False")
        self.assertGreaterEqual(inference_count, 1,
            "inference() call should have enable_text_splitting=False")


if __name__ == "__main__":
    # Run with verbosity
    unittest.main(verbosity=2)
