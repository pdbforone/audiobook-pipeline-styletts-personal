"""
Update Pronunciation Lexicon Tool

This tool reads potentially mispronounced words logged by the ASR validation
process, generates "say-as" phonetic hints for them using an LLM, and adds
them to the central pronunciation lexicon.

This creates a self-improving feedback loop for pronunciation.

Usage:
    python tools/update_lexicon.py
"""

import logging
import sys
from pathlib import Path

# Add project root to path to allow importing agents
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.llama_pronunciation_assistant import LlamaPronunciationAssistant

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

FEEDBACK_LOG_PATH = PROJECT_ROOT / ".pipeline" / "pronunciation_feedback.log"


def update_lexicon_from_feedback():
    """
    Reads words from the feedback log, generates pronunciations,
    and updates the central lexicon.
    """
    if not FEEDBACK_LOG_PATH.exists():
        logger.info("No pronunciation feedback log found. Nothing to do.")
        return

    try:
        with FEEDBACK_LOG_PATH.open("r", encoding="utf-8") as f:
            words_to_fix = {line.strip() for line in f if line.strip()}
    except Exception as e:
        logger.error(f"Could not read pronunciation feedback log: {e}")
        return

    if not words_to_fix:
        logger.info("Pronunciation feedback log is empty. Nothing to do.")
        return

    logger.info(f"Found {len(words_to_fix)} unique words for pronunciation review: {', '.join(words_to_fix)}")

    try:
        assistant = LlamaPronunciationAssistant()
    except Exception as e:
        logger.error(f"Failed to initialize LlamaPronunciationAssistant: {e}")
        logger.error("Ensure Ollama is running and the required model is available.")
        return

    new_pronunciations = 0
    for word in sorted(list(words_to_fix)):
        if word in assistant.pronunciation_dict:
            logger.info(f"Skipping '{word}': pronunciation already exists in the lexicon.")
            continue

        logger.info(f"Generating pronunciation for '{word}'...")
        try:
            pronunciation = assistant.generate_pronunciation(word)
            if pronunciation:
                logger.info(f"  -> Successfully generated 'say_as': {pronunciation.get('say_as')}")
                new_pronunciations += 1
            else:
                logger.warning(f"  -> Failed to generate pronunciation for '{word}'.")
        except Exception as e:
            logger.error(f"An error occurred while generating pronunciation for '{word}': {e}")

    logger.info(f"Lexicon update complete. Added {new_pronunciations} new pronunciations.")

    # Clear the log file after processing
    try:
        with FEEDBACK_LOG_PATH.open("w", encoding="utf-8") as f:
            f.write("")
        logger.info("Pronunciation feedback log has been cleared.")
    except Exception as e:
        logger.error(f"Failed to clear pronunciation feedback log: {e}")


if __name__ == "__main__":
    update_lexicon_from_feedback()
