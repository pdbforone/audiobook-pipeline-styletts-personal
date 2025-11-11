from phase4_tts_styletts.main import normalize_chunk_text


def test_normalize_chunk_text_collapses_spelled_words_and_whitespace():
    raw = "T h e   G i f t  \n o f   t h e   M a g i"
    assert normalize_chunk_text(raw) == "The Gift of the Magi."


def test_normalize_chunk_text_preserves_regular_words_and_punctuation():
    raw = "Mr. James D. Young said -\n\"Hello!\""
    assert normalize_chunk_text(raw) == 'Mr. James D. Young said - "Hello!"'


def test_normalize_chunk_text_handles_paragraph_breaks_and_final_period():
    raw = "She cried\n\nThen she smiled"
    assert normalize_chunk_text(raw) == "She cried. Then she smiled."
