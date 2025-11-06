"""
Extract timestamps of unwanted phrases from SRT file
This creates a list you can use to jump to each phrase in Audacity
"""

import srt
from pathlib import Path

def find_phrase_timestamps(srt_path: Path, target_phrases: list):
    """Find all timestamps where target phrases appear."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        subtitles = list(srt.parse(f.read()))
    
    matches = []
    for sub in subtitles:
        text = sub.content.lower()
        for phrase in target_phrases:
            if phrase.lower() in text:
                matches.append({
                    'index': sub.index,
                    'start': sub.start.total_seconds(),
                    'end': sub.end.total_seconds(),
                    'text': sub.content
                })
                break
    
    return matches

def format_timestamp(seconds):
    """Convert seconds to MM:SS.mmm format for Audacity."""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"

def main():
    srt_path = Path("processed/meditations_audiobook.srt")
    
    target_phrases = [
        "You need to add some text for me to talk",
        "You need to add text for me to talk"
    ]
    
    print("Scanning subtitles for unwanted phrases...")
    matches = find_phrase_timestamps(srt_path, target_phrases)
    
    print(f"\n{'='*70}")
    print(f"FOUND {len(matches)} INSTANCES")
    print(f"{'='*70}\n")
    
    # Write to file
    output_path = Path("phrase_timestamps.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("AUDACITY REMOVAL GUIDE\n")
        f.write("="*70 + "\n\n")
        f.write(f"Total instances: {len(matches)}\n\n")
        f.write("HOW TO USE:\n")
        f.write("1. Open meditations_audiobook.mp3 in Audacity\n")
        f.write("2. For each timestamp below:\n")
        f.write("   a. Press Ctrl+F to open 'Selection Toolbar'\n")
        f.write("   b. Enter the START time\n")
        f.write("   c. Listen to verify it's the phrase\n")
        f.write("   d. Select from START to END time\n")
        f.write("   e. Press Delete or Ctrl+K to remove\n\n")
        f.write("="*70 + "\n\n")
        
        for i, match in enumerate(matches, 1):
            start_time = format_timestamp(match['start'])
            end_time = format_timestamp(match['end'])
            f.write(f"[{i}/{len(matches)}] START: {start_time}  END: {end_time}\n")
            f.write(f"    Text: {match['text']}\n\n")
    
    # Console output
    print("FIRST 10 INSTANCES (for quick reference):")
    print("-"*70)
    for i, match in enumerate(matches[:10], 1):
        start_time = format_timestamp(match['start'])
        end_time = format_timestamp(match['end'])
        print(f"[{i}] {start_time} → {end_time}")
        print(f"    {match['text'][:60]}...")
    
    print(f"\n{'='*70}")
    print(f"📄 Full list saved to: {output_path}")
    print(f"   Use this file to guide your Audacity edits")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
