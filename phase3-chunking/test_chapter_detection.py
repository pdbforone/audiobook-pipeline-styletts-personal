"""
Create a new Phase 3 chunker that detects chapters instead of arbitrary word counts
"""
import re
from pathlib import Path
from typing import List, Tuple

def detect_chapters(text: str) -> List[Tuple[str, str]]:
    """
    Detect chapter boundaries in text.
    
    Returns list of (chapter_title, chapter_text) tuples.
    """
    chapters = []
    
    # Pattern for Roman numerals at start of line (I., II., III., etc.)
    # Matches: I., II., III., IV., V., VI., VII., VIII., IX., X., etc.
    chapter_pattern = r'^([IVX]+)\.\s*$'
    
    lines = text.split('\n')
    current_chapter_title = None
    current_chapter_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if this line is a chapter marker
        match = re.match(chapter_pattern, stripped)
        
        if match:
            # Save previous chapter if exists
            if current_chapter_title and current_chapter_lines:
                chapter_text = '\n'.join(current_chapter_lines).strip()
                if len(chapter_text) > 100:  # Only save substantial chapters
                    chapters.append((current_chapter_title, chapter_text))
            
            # Start new chapter
            current_chapter_title = f"Chapter {match.group(1)}"
            current_chapter_lines = []
        else:
            # Add line to current chapter
            if stripped:  # Skip empty lines
                current_chapter_lines.append(line)
    
    # Save final chapter
    if current_chapter_title and current_chapter_lines:
        chapter_text = '\n'.join(current_chapter_lines).strip()
        if len(chapter_text) > 100:
            chapters.append((current_chapter_title, chapter_text))
    
    # If no chapters detected, treat entire text as one chapter
    if not chapters:
        chapters.append(("Full Text", text.strip()))
    
    return chapters


def test_chapter_detection():
    """Test chapter detection on the Analects"""
    
    # Read the extracted text
    text_file = Path("C:/Users/myson/Pipeline/audiobook-pipeline/phase2-extraction/src/extracted_text/The_Analects_of_Confucius_20240228.txt")
    
    with open(text_file, 'r', encoding='utf-8') as f:
        text = f.read()
    
    chapters = detect_chapters(text)
    
    print(f"Detected {len(chapters)} chapters:\n")
    
    for i, (title, content) in enumerate(chapters, 1):
        word_count = len(content.split())
        char_count = len(content)
        first_100_chars = content[:100].replace('\n', ' ')
        
        print(f"{i}. {title}")
        print(f"   Words: {word_count:,} | Characters: {char_count:,}")
        print(f"   Preview: {first_100_chars}...")
        print()
    
    total_words = sum(len(content.split()) for _, content in chapters)
    print(f"Total: {len(chapters)} chapters, {total_words:,} words")
    print(f"\nCompare to current: 109 chunks (too many!)")
    print(f"New approach: {len(chapters)} chapters (better for TTS)")


if __name__ == "__main__":
    test_chapter_detection()
