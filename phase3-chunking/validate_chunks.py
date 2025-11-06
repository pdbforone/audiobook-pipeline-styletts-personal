"""
Chunk Validation Script - Check for incomplete chunks

Usage:
    python validate_chunks.py [chunks_directory]

Example:
    python validate_chunks.py "C:\\Users\\myson\\Pipeline\\audiobook-pipeline-chatterbox\\phase3-chunking\\chunks"
"""

import os
import re
import sys
from pathlib import Path
from typing import Tuple, List


def is_complete_chunk(text: str) -> Tuple[bool, str]:
    """
    Check if a chunk ends on a complete thought.
    
    Detects incomplete patterns:
    - Prepositions at end
    - Relative clauses
    - Conjunctions
    - Auxiliary verbs
    - Unbalanced quotes
    - Trailing commas/semicolons
    """
    text = text.strip()
    
    if not text:
        return False, "Empty text"
    
    # Check for unbalanced quotes
    double_quotes = text.count('"')
    if double_quotes % 2 != 0:
        return False, "Unbalanced double quotes"
    
    # Comprehensive incomplete endings patterns
    incomplete_patterns = [
        # Prepositions
        (r'\b(to|for|with|from|by|at|in|on|of|about|before|after|during|through|between|among|within|without|against|upon)\s*$', 
         "preposition"),
        
        # Articles
        (r'\b(the|a|an)\s*$', 
         "article"),
        
        # Relative pronouns
        (r'\b(which|that|who|whom|whose|where|when)\s*$', 
         "relative pronoun"),
        
        # Subordinating conjunctions
        (r'\b(because|although|though|while|since|unless|if|when|where|before|after|until|as|so|than)\s*$', 
         "subordinating conjunction"),
        
        # Coordinating conjunctions
        (r'\b(and|but|or|yet|so|nor|for)\s*$', 
         "coordinating conjunction"),
        
        # Auxiliary verbs
        (r'\b(is|are|was|were|has|have|had|will|would|can|could|should|may|might|must|do|does|did)\s*$', 
         "auxiliary verb"),
        
        # Trailing punctuation
        (r',\s*$', 
         "trailing comma"),
        
        (r';\s*$', 
         "trailing semicolon"),
    ]
    
    for pattern, pattern_name in incomplete_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return False, f"ends with {pattern_name} ('{match.group().strip()}')"
    
    # Check for dialogue introducers
    dialogue_patterns = [
        r'\bsaid,?\s*$',
        r'\breplied,?\s*$',
        r'\basked,?\s*$',
        r'\banswered,?\s*$',
    ]
    
    for pattern in dialogue_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return False, "dialogue introducer without dialogue"
    
    return True, "Complete"


def get_chunk_preview(text: str, length: int = 100) -> str:
    """Get the end preview of a chunk."""
    if len(text) <= length:
        return text
    return "..." + text[-length:]


def validate_chunks_in_directory(chunks_dir: str) -> None:
    """
    Validate all chunks in a directory.
    
    Prints report of incomplete chunks and summary statistics.
    """
    chunks_path = Path(chunks_dir)
    
    if not chunks_path.exists():
        print(f"❌ Error: Directory not found: {chunks_dir}")
        return
    
    chunk_files = sorted(chunks_path.glob("*.txt"))
    
    if not chunk_files:
        print(f"❌ Error: No .txt files found in {chunks_dir}")
        return
    
    print(f"\n{'='*80}")
    print(f"CHUNK VALIDATION REPORT")
    print(f"{'='*80}")
    print(f"Directory: {chunks_dir}")
    print(f"Total chunks: {len(chunk_files)}")
    print(f"{'='*80}\n")
    
    incomplete_chunks = []
    complete_chunks = []
    
    for chunk_file in chunk_files:
        try:
            with open(chunk_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            is_comp, reason = is_complete_chunk(text)
            char_count = len(text)
            word_count = len(text.split())
            
            if not is_comp:
                incomplete_chunks.append({
                    'name': chunk_file.name,
                    'reason': reason,
                    'preview': get_chunk_preview(text),
                    'chars': char_count,
                    'words': word_count
                })
            else:
                complete_chunks.append({
                    'name': chunk_file.name,
                    'chars': char_count,
                    'words': word_count
                })
        
        except Exception as e:
            print(f"⚠️  Error reading {chunk_file.name}: {e}")
    
    # Print incomplete chunks (if any)
    if incomplete_chunks:
        print(f"❌ INCOMPLETE CHUNKS DETECTED: {len(incomplete_chunks)}\n")
        print(f"{'-'*80}\n")
        
        for i, chunk_info in enumerate(incomplete_chunks, 1):
            print(f"Chunk #{i}: {chunk_info['name']}")
            print(f"  Reason: {chunk_info['reason']}")
            print(f"  Size: {chunk_info['chars']} chars, {chunk_info['words']} words")
            print(f"  Ends with: {chunk_info['preview']}")
            print()
    else:
        print(f"✅ ALL CHUNKS COMPLETE!\n")
    
    # Print summary statistics
    print(f"{'-'*80}")
    print(f"SUMMARY")
    print(f"{'-'*80}")
    print(f"✅ Complete chunks: {len(complete_chunks)} ({len(complete_chunks)/len(chunk_files)*100:.1f}%)")
    print(f"❌ Incomplete chunks: {len(incomplete_chunks)} ({len(incomplete_chunks)/len(chunk_files)*100:.1f}%)")
    
    if complete_chunks:
        avg_chars = sum(c['chars'] for c in complete_chunks) / len(complete_chunks)
        avg_words = sum(c['words'] for c in complete_chunks) / len(complete_chunks)
        print(f"\nComplete chunks stats:")
        print(f"  Average size: {avg_chars:.0f} chars, {avg_words:.0f} words")
    
    print(f"{'='*80}\n")
    
    # Exit code
    if incomplete_chunks:
        print("❌ VALIDATION FAILED: Incomplete chunks detected")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED: All chunks are complete")
        sys.exit(0)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        # Default to current directory's chunks folder
        chunks_dir = Path.cwd() / "chunks"
        if not chunks_dir.exists():
            print("Usage: python validate_chunks.py [chunks_directory]")
            print("\nExample:")
            print('  python validate_chunks.py "C:\\Users\\myson\\Pipeline\\audiobook-pipeline-chatterbox\\phase3-chunking\\chunks"')
            sys.exit(1)
    else:
        chunks_dir = sys.argv[1]
    
    validate_chunks_in_directory(chunks_dir)


if __name__ == "__main__":
    main()
