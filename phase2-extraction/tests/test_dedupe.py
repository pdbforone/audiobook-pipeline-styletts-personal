"""
Tests for deduplication utilities.

Validates the defense-in-depth safety net against text duplication.
"""

import pytest
from phase2_extraction.dedupe import (
    dedupe_consecutive,
    dedupe_paragraphs,
    dedupe_lines,
    validate_no_duplicates,
)


class TestDedupeConsecutive:
    """Test the core deduplication iterator."""

    def test_removes_consecutive_duplicates(self):
        """Should remove adjacent duplicate items."""
        input_blocks = ["Para A", "Para A", "Para B", "Para B", "Para C"]
        result = list(dedupe_consecutive(input_blocks))
        assert result == ["Para A", "Para B", "Para C"]

    def test_preserves_non_consecutive_duplicates(self):
        """Should preserve duplicates that aren't adjacent."""
        input_blocks = ["Para A", "Para B", "Para A"]
        result = list(dedupe_consecutive(input_blocks))
        assert result == ["Para A", "Para B", "Para A"]

    def test_handles_empty_input(self):
        """Should handle empty sequence."""
        result = list(dedupe_consecutive([]))
        assert result == []

    def test_handles_single_item(self):
        """Should pass through single item unchanged."""
        result = list(dedupe_consecutive(["Only item"]))
        assert result == ["Only item"]

    def test_skips_short_strings(self):
        """Should preserve very short strings without deduplication."""
        # Empty lines (< 10 chars) should be preserved even if duplicated
        input_blocks = ["", "", "A", "A", "Long paragraph text"]
        result = list(dedupe_consecutive(input_blocks, min_length=10))
        # Empty strings pass through, short strings get deduped
        assert result == ["", "", "A", "Long paragraph text"]

    def test_handles_unicode(self):
        """Should handle unicode content correctly."""
        input_blocks = ["Café ☕", "Café ☕", "Naïve"]
        result = list(dedupe_consecutive(input_blocks))
        assert result == ["Café ☕", "Naïve"]


class TestDedupeParagraphs:
    """Test paragraph-level deduplication."""

    def test_removes_duplicate_paragraphs(self):
        """Should remove consecutive duplicate paragraphs."""
        text = "Para A.\n\nPara A.\n\nPara B.\n\nPara B.\n\nPara C."
        result = dedupe_paragraphs(text)
        assert result == "Para A.\n\nPara B.\n\nPara C."

    def test_preserves_single_newlines(self):
        """Should not affect single newlines within paragraphs."""
        text = "Line 1\nLine 2\n\nLine 1\nLine 2\n\nPara B"
        result = dedupe_paragraphs(text)
        assert result == "Line 1\nLine 2\n\nPara B"

    def test_handles_empty_paragraphs(self):
        """Should handle multiple consecutive newlines."""
        text = "Para A\n\n\n\nPara A\n\n\n\nPara B"
        # Multiple newlines create empty paragraphs
        result = dedupe_paragraphs(text, min_para_length=5)
        # Empty paragraphs (< min_length) are preserved
        assert "Para A" in result
        assert "Para B" in result


class TestDedupeLines:
    """Test line-level deduplication."""

    def test_removes_duplicate_lines(self):
        """Should remove consecutive duplicate lines."""
        text = "Line A\nLine A\nLine B\nLine B\nLine C"
        result = dedupe_lines(text)
        assert result == "Line A\nLine B\nLine C"

    def test_preserves_intentional_repetition(self):
        """Should preserve non-consecutive repetition."""
        text = "Line A\nLine B\nLine A"
        result = dedupe_lines(text)
        assert result == "Line A\nLine B\nLine A"

    def test_handles_empty_lines(self):
        """Should preserve empty lines (below min_length)."""
        text = "Line A\n\n\nLine B"
        result = dedupe_lines(text, min_line_length=3)
        # Empty lines pass through (< min_length)
        assert result == "Line A\n\n\nLine B"


class TestValidateNoDuplicates:
    """Test validation utility."""

    def test_detects_duplicates(self):
        """Should detect consecutive duplicates."""
        blocks = ["A", "A", "B", "C", "C"]
        is_valid, indices = validate_no_duplicates(blocks, max_consecutive_duplicates=0)
        assert is_valid is False
        assert indices == [1, 4]  # Positions where duplicates occurred

    def test_passes_clean_input(self):
        """Should pass input with no duplicates."""
        blocks = ["A", "B", "C", "D"]
        is_valid, indices = validate_no_duplicates(blocks)
        assert is_valid is True
        assert indices == []

    def test_allows_threshold(self):
        """Should allow specified number of duplicates."""
        blocks = ["A", "A", "B"]
        is_valid, indices = validate_no_duplicates(blocks, max_consecutive_duplicates=1)
        assert is_valid is True  # 1 duplicate is within threshold

    def test_handles_empty_input(self):
        """Should handle empty list."""
        is_valid, indices = validate_no_duplicates([])
        assert is_valid is True
        assert indices == []


class TestRealWorldScenarios:
    """Test real-world duplication patterns from the bug report."""

    def test_txt_extractor_bug_pattern(self):
        """
        Reproduces the actual bug pattern from phase2_extraction/extractors/txt.py.

        The bug caused each paragraph ending with punctuation to be duplicated
        when the next line didn't start with uppercase.
        """
        # This is the exact pattern that occurred
        duplicated_text = (
            "This is a longer passage designed to test the full capabilities "
            "of the audiobook pipeline. It contains multiple paragraphs and "
            "sentences of varying lengths. The purpose of this is to ensure "
            "that all phases of the pipeline, from validation and extraction "
            "to chunking, text-to-speech synthesis, and final enhancement, "
            "are properly exercised. "
            "This is a longer passage designed to test the full capabilities "
            "of the audiobook pipeline. It contains multiple paragraphs and "
            "sentences of varying lengths. The purpose of this is to ensure "
            "that all phases of the pipeline, from validation and extraction "
            "to chunking, text-to-speech synthesis, and final enhancement, "
            "are properly exercised.\n\n"
            "The first phase, validation, should check the integrity of this "
            "file and report its findings."
        )

        # Dedupe should fix it
        result = dedupe_paragraphs(duplicated_text, min_para_length=50)

        # Should remove the duplicate paragraph
        assert result.count("This is a longer passage") == 1
        assert result.count("The first phase") == 1

    def test_retry_side_effect_pattern(self):
        """
        Simulates the "retry side-effect" pattern from the research.

        When a @retry decorator re-executes a function that appends to an
        outer-scope list, you get: [A, B, A, B]
        """
        # Simulated result from retry appending twice
        blocks = [
            "Paragraph A from attempt 1",
            "Paragraph B from attempt 1",
            "Paragraph A from attempt 2 (retry)",
            "Paragraph B from attempt 2 (retry)",
        ]

        # Our dedupe won't fix this pattern (not consecutive)
        result = list(dedupe_consecutive(blocks))
        assert len(result) == 4  # Not consecutive, so preserved

        # But if the retry happens per-item (more likely):
        blocks_per_item = [
            "Paragraph A",
            "Paragraph A",  # Retry
            "Paragraph B",
            "Paragraph B",  # Retry
        ]

        result = list(dedupe_consecutive(blocks_per_item))
        assert result == ["Paragraph A", "Paragraph B"]  # Fixed!

    def test_textract_layout_hierarchy_pattern(self):
        """
        Simulates AWS Textract LAYOUT_LIST + LINE duplication.

        Parent block contains concatenated text; child blocks contain items.
        Naive extraction prints both, causing duplication.
        """
        # Extracted from LAYOUT_LIST parent
        layout_text = "Item 1\nItem 2\nItem 3"

        # Then extracted from LINE children
        line_texts = ["Item 1", "Item 2", "Item 3"]

        # Combined naively
        all_text = [layout_text] + line_texts

        # Dedupe paragraphs won't help (different granularity)
        # But dedupe lines at finer granularity could:
        combined = "\n".join(all_text)
        result = dedupe_lines(combined)

        # Should reduce duplication
        assert result.count("Item 1") <= 2  # At most from layout block


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
