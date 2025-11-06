"""
Test for chunk size optimization and duration prediction.
"""

import pytest
from phase3_chunking.utils import (
    _chunk_by_char_count,
    _split_oversized_sentence,
    predict_duration,
    calculate_chunk_metrics,
    form_semantic_chunks,
)


def test_predict_duration_chars():
    """Test duration prediction using character count."""
    # 750 chars/min = 12.5 chars/sec
    # 500 chars should be ~40 seconds
    text = "A" * 500
    duration = predict_duration(text, method="chars")
    assert 35 < duration < 45, f"Expected ~40s, got {duration}s"


def test_predict_duration_words():
    """Test duration prediction using word count."""
    # 150 words/min = 2.5 words/sec
    # 50 words should be ~20 seconds
    text = " ".join(["word"] * 50)
    duration = predict_duration(text, method="words")
    assert 18 < duration < 22, f"Expected ~20s, got {duration}s"


def test_chunk_by_char_count_normal():
    """Test character-based chunking with normal sentences."""
    sentences = [
        "This is sentence one with some content here.",
        "This is sentence two with more content.",
        "This is sentence three with even more content.",
        "This is sentence four continuing the pattern.",
    ]
    
    # With min=100, max=200, should create 2-3 chunks
    chunks = _chunk_by_char_count(sentences, min_chars=100, max_chars=200)
    
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
    for chunk in chunks:
        assert len(chunk) <= 200, f"Chunk exceeds 200 chars: {len(chunk)}"


def test_chunk_by_char_count_oversized():
    """Test chunking with an oversized sentence (>600 chars)."""
    short_sent = "Short sentence."
    long_sent = "A" * 700  # Oversized sentence
    sentences = [short_sent, long_sent, short_sent]
    
    chunks = _chunk_by_char_count(sentences, min_chars=400, max_chars=600)
    
    # Should have at least 3 chunks (short, split long, short)
    assert len(chunks) >= 3, f"Expected >= 3 chunks, got {len(chunks)}"
    
    # All chunks should be <= 600 chars
    for i, chunk in enumerate(chunks):
        assert len(chunk) <= 600, f"Chunk {i} exceeds 600 chars: {len(chunk)}"


def test_split_oversized_sentence_semicolon():
    """Test splitting oversized sentence on semicolons."""
    sentence = "Part one with content; part two with more content; part three with even more content"
    
    sub_chunks = _split_oversized_sentence(sentence, max_chars=50)
    
    assert len(sub_chunks) >= 2, "Should split into multiple chunks"
    for chunk in sub_chunks:
        assert len(chunk) <= 50, f"Sub-chunk exceeds 50 chars: {len(chunk)}"


def test_split_oversized_sentence_words():
    """Test splitting oversized sentence on word boundaries."""
    # No punctuation, just words
    sentence = " ".join(["word"] * 100)  # Very long sentence
    
    sub_chunks = _split_oversized_sentence(sentence, max_chars=100)
    
    assert len(sub_chunks) >= 2, "Should split into multiple chunks"
    for chunk in sub_chunks:
        assert len(chunk) <= 100, f"Sub-chunk exceeds 100 chars: {len(chunk)}"


def test_calculate_chunk_metrics():
    """Test chunk metrics calculation."""
    chunks = [
        "This is chunk one with some content.",
        "This is chunk two with different content and more words for testing.",
        "Short chunk.",
    ]
    
    metrics = calculate_chunk_metrics(chunks)
    
    # Check all expected keys are present
    assert "chunk_char_lengths" in metrics
    assert "chunk_word_counts" in metrics
    assert "chunk_durations" in metrics
    assert "avg_char_length" in metrics
    assert "avg_word_count" in metrics
    assert "avg_duration" in metrics
    assert "max_duration" in metrics
    assert "min_duration" in metrics
    
    # Check lengths match
    assert len(metrics["chunk_char_lengths"]) == 3
    assert len(metrics["chunk_word_counts"]) == 3
    assert len(metrics["chunk_durations"]) == 3
    
    # Check values are reasonable
    assert metrics["avg_char_length"] > 0
    assert metrics["avg_word_count"] > 0
    assert metrics["avg_duration"] > 0
    assert metrics["max_duration"] >= metrics["min_duration"]


def test_calculate_chunk_metrics_empty():
    """Test chunk metrics with empty input."""
    metrics = calculate_chunk_metrics([])
    
    assert metrics["chunk_char_lengths"] == []
    assert metrics["avg_char_length"] == 0
    assert metrics["avg_duration"] == 0


def test_form_semantic_chunks_char_optimization():
    """Test that form_semantic_chunks creates chunks within character limits."""
    # Create sentences that will exceed 600 chars if combined naively
    sentences = [
        "This is a test sentence with reasonable length for testing purposes.",
        "Another sentence that adds more content to the overall text being chunked.",
        "A third sentence continuing the pattern of adding substantial content.",
        "Yet another sentence to ensure we have enough text for multiple chunks.",
        "And one more sentence to complete our test data with sufficient length.",
    ]
    
    # Each sentence is ~70-80 chars, so we should get chunks that respect 600 char limit
    chunks, coherence, embeddings = form_semantic_chunks(
        sentences, min_words=80, max_words=120
    )
    
    assert len(chunks) > 0, "Should create at least one chunk"
    
    # Verify all chunks are within character limits
    for i, chunk in enumerate(chunks):
        char_count = len(chunk)
        duration = predict_duration(chunk, method="chars")
        
        # Chunks should be optimized for Phase 4 (400-600 chars preferred)
        # Allow some flexibility for edge cases
        assert char_count <= 650, f"Chunk {i} exceeds soft limit: {char_count} chars"
        
        # Duration should be under 30s (with some buffer)
        assert duration < 30, f"Chunk {i} duration too long: {duration}s"
    
    # Verify coherence scores exist
    assert len(coherence) == len(chunks) - 1, "Should have n-1 coherence scores"
    
    # Verify embeddings exist
    assert len(embeddings) == len(chunks), "Should have n embeddings"


def test_chunk_size_cap_enforcement():
    """Test that chunks are capped at max_chars even with long sentences."""
    # Create a very long sentence that needs splitting
    long_sentence = " ".join(["word"] * 200)  # ~1000+ chars
    sentences = [long_sentence]
    
    chunks = _chunk_by_char_count(sentences, min_chars=400, max_chars=600)
    
    # Should split into multiple chunks
    assert len(chunks) >= 2, f"Long sentence should split into multiple chunks, got {len(chunks)}"
    
    # All chunks must respect the 600 char limit
    for i, chunk in enumerate(chunks):
        assert len(chunk) <= 600, f"Chunk {i} exceeds 600 char limit: {len(chunk)} chars"


def test_duration_prediction_accuracy():
    """Test that duration predictions are reasonable for various text lengths."""
    test_cases = [
        ("A" * 375, 30),  # 375 chars ≈ 30s at 750 cpm
        ("A" * 500, 40),  # 500 chars ≈ 40s
        ("A" * 250, 20),  # 250 chars ≈ 20s
    ]
    
    for text, expected_duration in test_cases:
        duration = predict_duration(text, method="chars")
        # Allow 20% margin
        lower = expected_duration * 0.8
        upper = expected_duration * 1.2
        assert lower <= duration <= upper, (
            f"Duration {duration}s outside expected range [{lower}, {upper}] "
            f"for {len(text)} chars (expected ~{expected_duration}s)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
