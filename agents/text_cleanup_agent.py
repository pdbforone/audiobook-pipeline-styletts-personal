# agents/text_cleanup_agent.py

import logging
from typing import Dict, Any

try:
    from .llama_base import LlamaAgent
except ImportError:
    # Handle the case where this is run as a standalone script
    from llama_base import LlamaAgent

logger = logging.getLogger(__name__)

class TextCleanupAgent(LlamaAgent):
    """
    An agent that uses an LLM to clean and reformat raw extracted text.
    """

    def __init__(self, model: str = "phi3:mini", config: Dict[str, Any] = None):
        super().__init__(model=model, config=config)
        self.system_prompt = """You are an expert text editor for an audiobook production pipeline. Your task is to clean and reformat raw text extracted from a book.

You must perform the following actions:
1.  **Remove Non-Content**: Eliminate page numbers, headers, footers, tables of contents, and any other text that is not part of the main narrative.
2.  **Fix OCR Errors**: Correct common optical character recognition errors (e.g., "rn" becomes "m", "I" becomes "l" or "1").
3.  **Standardize Paragraphs**: Ensure paragraphs are separated by a single newline. Remove any unnecessary line breaks within paragraphs.
4.  **Format Dialogue**: Ensure dialogue is correctly formatted with standard quotation marks.
5.  **Preserve Structure**: Retain chapter titles and section breaks, marking them clearly (e.g., "Chapter 1").

You must only output the cleaned, corrected text. Do not add any commentary or explanation. Preserve the original language and meaning of the text perfectly."""

    def clean_text(self, raw_text: str) -> str:
        """
        Uses the LLM to clean the provided raw text.

        Args:
            raw_text: The raw text extracted from a book file.

        Returns:
            The cleaned and reformatted text.
        """
        logger.info(f"Starting text cleanup with model {self.model}...")

        # For very long texts, it's better to process in chunks
        # This is a simplified approach for now.
        if len(raw_text) > 15000:
            logger.warning("Input text is very long. Processing the full text at once may be slow or fail. A chunking strategy for cleanup is recommended for production use.")

        prompt = f"Clean the following text for an audiobook:\n\n---\n\n{raw_text}"

        try:
            cleaned_text = self.query(prompt)
            logger.info("Successfully cleaned text using LLM.")
            return cleaned_text
        except Exception as e:
            logger.error(f"Failed to clean text using LLM: {e}")
            # Fallback to returning the original text if the LLM fails
            return raw_text

if __name__ == '__main__':
    # This is an example of how to use the agent.
    # It requires the LlamaAgent base class and an Ollama server to be running.
    sample_text = """
    Chapter 1

    It was the best of times, it was the worst of tirnes, it was the age of wisdom, it was the age of foolishness...

    Page 1

    another paragraph here.
    """

    print("--- RAW TEXT ---")
    print(sample_text)

    # In a real scenario, you would need to have the llama_base.py in the same directory
    # or in the python path, and an ollama server running.
    # This is a placeholder for a functional example.
    try:
        cleanup_agent = TextCleanupAgent()
        cleaned = cleanup_agent.clean_text(sample_text)
        
        print("\n--- CLEANED TEXT ---")
        print(cleaned)

    except Exception as e:
        print(f"\nCould not run example: {e}")
        print("This example requires a running Ollama server and the LlamaAgent base class.")
