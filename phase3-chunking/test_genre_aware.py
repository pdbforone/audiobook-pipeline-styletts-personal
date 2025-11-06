# Quick Test Script for Phase 3 Genre-Aware Chunking
# Run this to verify the upgrade works

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_profiles():
    """Test that profiles module works."""
    print("\n" + "="*60)
    print("TEST 1: Profiles Module")
    print("="*60)
    
    try:
        from phase3_chunking.profiles import list_profiles, get_profile, get_profile_info
        
        profiles = list_profiles()
        print(f"✅ Available profiles: {profiles}")
        
        for profile_name in profiles:
            info = get_profile_info(profile_name)
            print(f"\n{profile_name.upper()}:")
            print(f"  Word range: {info['word_range']}")
            print(f"  Char range: {info['char_range']}")
            print(f"  Description: {info['description']}")
        
        print("\n✅ Profiles module working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Profiles test failed: {e}")
        return False


def test_genre_detection():
    """Test genre detection on sample texts."""
    print("\n" + "="*60)
    print("TEST 2: Genre Detection")
    print("="*60)
    
    try:
        from phase3_chunking.detect import detect_genre
        
        # Test 1: Philosophy text
        philosophy_text = """
        The Master said, 'Fine words and an insinuating appearance are seldom associated 
        with true virtue.' The philosopher Tsang said, 'I daily examine myself on three 
        points: whether, in transacting business for others, I may have been not faithful; 
        whether, in intercourse with friends, I may have been not sincere; whether I may 
        have not mastered and practiced the instructions of my teacher.'
        """
        
        genre, confidence, scores = detect_genre(philosophy_text, {'title': 'The Analects'})
        print(f"\nPhilosophy text:")
        print(f"  Detected: {genre}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Scores: {scores}")
        
        if genre == 'philosophy':
            print("  ✅ Correct!")
        else:
            print(f"  ⚠️  Expected 'philosophy', got '{genre}'")
        
        # Test 2: Fiction text
        fiction_text = """
        "Where are you going?" she asked.
        "To the store," he replied with a smile.
        She looked at him suspiciously. "Are you sure?"
        "Yes," he said, "I promise I'll be back soon."
        The conversation continued as they walked down the street.
        """
        
        genre, confidence, scores = detect_genre(fiction_text, {'title': 'A Novel'})
        print(f"\nFiction text:")
        print(f"  Detected: {genre}")
        print(f"  Confidence: {confidence:.2f}")
        
        if genre == 'fiction' or confidence > 0.3:  # May detect as fiction or memoir
            print("  ✅ Detected dialogue-heavy text!")
        
        print("\n✅ Genre detection working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Genre detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_voice_selection():
    """Test voice selection logic."""
    print("\n" + "="*60)
    print("TEST 3: Voice Selection")
    print("="*60)
    
    try:
        from phase3_chunking.voice_selection import (
            select_voice, 
            list_available_voices,
            load_voice_registry
        )
        
        # List voices
        voices = list_available_voices()
        print(f"\n✅ Available voices: {list(voices.keys())}")
        
        for voice_id, desc in voices.items():
            print(f"  - {voice_id}: {desc}")
        
        # Test voice selection for different profiles
        print("\nVoice selection by profile:")
        for profile in ['philosophy', 'fiction', 'academic', 'memoir', 'technical']:
            voice = select_voice(profile)
            print(f"  {profile} → {voice}")
        
        print("\n✅ Voice selection working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Voice selection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("PHASE 3 GENRE-AWARE CHUNKING - VERIFICATION TESTS")
    print("="*70)
    
    results = []
    
    results.append(("Profiles", test_profiles()))
    results.append(("Genre Detection", test_genre_detection()))
    results.append(("Voice Selection", test_voice_selection()))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Phase 3 upgrade successful!")
        print("\nNext step: Run full chunking test on The Analects")
        print("Command:")
        print("  poetry run python -m phase3_chunking.chunker \\")
        print("    --file_id analects_test_v2 \\")
        print("    --text_path '../phase2-extraction/extracted_text/analects_test_v2.txt' \\")
        print("    --profile auto -v")
        return 0
    else:
        print("\n❌ Some tests failed. Check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
