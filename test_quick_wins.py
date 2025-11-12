#!/usr/bin/env python3
"""
🧪 Quick Wins Test Suite
Tests all installed components for Personal Audiobook Studio
"""

import sys
from pathlib import Path
from typing import Dict, Tuple

# ANSI colors for beautiful terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a beautiful header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}")
    print(f"{text}")
    print(f"{'='*70}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")


def test_import(package: str, display_name: str = None) -> Tuple[bool, str]:
    """
    Test if a package can be imported

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    if display_name is None:
        display_name = package

    try:
        __import__(package)
        return True, ""
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def test_silero_vad() -> bool:
    """Test Silero VAD installation"""
    print_header("🎯 Testing Silero VAD")

    print_info("Checking silero_vad import...")
    success, error = test_import("silero_vad")

    if not success:
        print_error(f"Failed: {error}")
        print_info("Install: pip install silero-vad")
        return False

    try:
        from silero_vad import load_silero_vad

        print_info("Loading VAD model...")
        model = load_silero_vad()

        print_success("Silero VAD loaded successfully!")
        print_info("  Features: Neural silence detection")
        print_info("  Model size: 1.8 MB")
        print_info("  Processing: <1ms per chunk")
        print_info("  Impact: 🔥🔥🔥🔥 Surgical crossfades")
        return True

    except Exception as e:
        print_error(f"Failed to load model: {e}")
        return False


def test_deepfilternet() -> bool:
    """Test DeepFilterNet installation"""
    print_header("🔇 Testing DeepFilterNet")

    print_info("Checking DeepFilterNet import...")

    try:
        from df import enhance, init_df

        print_success("DeepFilterNet imported successfully!")
        print_info("  Type: Neural noise suppression")
        print_info("  Model: DeepFilterNet3")
        print_info("  Quality: Professional-grade")
        print_info("  Impact: 🔥🔥🔥 Pro clarity")
        print_info("  Note: Already integrated in Phase 5!")
        return True

    except ImportError as e:
        print_error(f"Failed: {e}")
        print_info("Install: pip install deepfilternet")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_openvoice() -> bool:
    """Test OpenVoice v2 installation"""
    print_header("🎙️ Testing OpenVoice v2")

    print_info("Checking OpenVoice import...")

    try:
        from openvoice import se_extractor

        print_success("OpenVoice v2 imported successfully!")
        print_info("  Features: Emotion control, instant voice cloning")
        print_info("  Clone time: 1-5 seconds of audio")
        print_info("  Emotions: Contemplative, dramatic, warm, etc.")
        print_info("  Languages: English, Spanish, French, Chinese, Japanese, Korean")
        print_info("  Impact: 🔥🔥🔥🔥🔥 GAME CHANGER")
        print_info("  License: MIT (free for personal use)")
        return True

    except ImportError as e:
        print_error(f"Failed: {e}")
        print_info("Install:")
        print_info("  git clone https://github.com/myshell-ai/OpenVoice")
        print_info("  cd OpenVoice && pip install -e .")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_pedalboard() -> bool:
    """Test Pedalboard installation"""
    print_header("🎚️ Testing Pedalboard")

    print_info("Checking Pedalboard import...")
    success, error = test_import("pedalboard")

    if not success:
        print_error(f"Failed: {error}")
        print_info("Install: pip install pedalboard")
        return False

    try:
        from pedalboard import Pedalboard, Compressor, Reverb

        print_success("Pedalboard loaded successfully!")
        print_info("  Source: Spotify's audio library")
        print_info("  Features: Professional effects")
        print_info("  Effects: Compressor, EQ, Reverb, Limiter, etc.")
        print_info("  Impact: 🔥🔥🔥🔥 Pro mastering")
        print_info("  License: GPL-2.0 (OK for personal use)")
        return True

    except Exception as e:
        print_error(f"Failed to load: {e}")
        return False


def test_gradio() -> bool:
    """Test Gradio installation"""
    print_header("🎨 Testing Gradio UI")

    print_info("Checking Gradio import...")
    success, error = test_import("gradio")

    if not success:
        print_error(f"Failed: {error}")
        print_info("Install: pip install gradio>=4.0.0")
        return False

    try:
        import gradio as gr

        print_success("Gradio loaded successfully!")
        print_info(f"  Version: {gr.__version__}")
        print_info("  Purpose: Beautiful web interface")
        print_info("  Launch: python ui/app.py")
        print_info("  Impact: 🔥🔥🔥🔥 Joyful UX")
        return True

    except Exception as e:
        print_error(f"Failed to load: {e}")
        return False


def test_f5_tts() -> bool:
    """Test F5-TTS installation (optional)"""
    print_header("🚀 Testing F5-TTS (Optional)")

    print_info("Checking F5-TTS import...")

    try:
        from f5_tts.api import F5TTS

        print_success("F5-TTS imported successfully!")
        print_info("  Features: Superior prosody, natural rhythm")
        print_info("  Quality: State-of-the-art (2024)")
        print_info("  Speed: ~4.5 hours per 100k-word book")
        print_info("  Impact: 🔥🔥🔥🔥🔥 Excellent quality")
        print_info("  License: MIT")
        return True

    except ImportError:
        print_warning("F5-TTS not installed (optional)")
        print_info("Install:")
        print_info("  git clone https://github.com/SWivid/F5-TTS")
        print_info("  cd F5-TTS && pip install -e .")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_xtts() -> bool:
    """Test XTTS v2 installation (optional)"""
    print_header("🌍 Testing XTTS v2 (Optional)")

    print_info("Checking XTTS import...")

    try:
        from TTS.api import TTS

        print_success("XTTS v2 imported successfully!")
        print_info("  Features: 17 languages, versatile")
        print_info("  Languages: EN, ES, FR, DE, IT, PT, PL, TR, RU, NL, etc.")
        print_info("  Quality: Excellent")
        print_info("  Impact: 🔥🔥🔥🔥 Multilingual")
        print_info("  License: Coqui Public (non-commercial OK)")
        return True

    except ImportError:
        print_warning("XTTS v2 not installed (optional)")
        print_info("Install: pip install TTS")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def test_bark() -> bool:
    """Test Bark installation (optional)"""
    print_header("🎭 Testing Bark (Optional)")

    print_info("Checking Bark import...")

    try:
        from bark import SAMPLE_RATE, generate_audio

        print_success("Bark imported successfully!")
        print_info("  Features: Laughter, sighs, emotion, music")
        print_info("  Expressiveness: Ultra-high (non-verbal cues)")
        print_info("  Speed: Slower (~3-5x vs F5-TTS)")
        print_info("  Impact: 🔥🔥🔥🔥🔥 Dramatic moments")
        print_info("  License: MIT")
        return True

    except ImportError:
        print_warning("Bark not installed (optional)")
        print_info("Install: pip install git+https://github.com/suno-ai/bark.git")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False


def run_all_tests() -> Dict[str, bool]:
    """Run all tests and return results"""

    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║           🧪 PERSONAL AUDIOBOOK STUDIO TEST SUITE 🧪               ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")

    results = {}

    # Core Quick Wins
    print_info("Testing Quick Win components...")
    results['Silero VAD'] = test_silero_vad()
    results['DeepFilterNet'] = test_deepfilternet()
    results['OpenVoice v2'] = test_openvoice()
    results['Pedalboard'] = test_pedalboard()
    results['Gradio UI'] = test_gradio()

    # Optional advanced components
    print_info("\nTesting optional advanced components...")
    results['F5-TTS'] = test_f5_tts()
    results['XTTS v2'] = test_xtts()
    results['Bark'] = test_bark()

    return results


def print_summary(results: Dict[str, bool]):
    """Print test summary"""
    print_header("📊 TEST SUMMARY")

    # Categorize results
    quick_wins = ['Silero VAD', 'DeepFilterNet', 'OpenVoice v2', 'Pedalboard', 'Gradio UI']
    optional = ['F5-TTS', 'XTTS v2', 'Bark']

    print(f"{Colors.BOLD}Quick Win Components:{Colors.ENDC}")
    for component in quick_wins:
        status = "✅ READY" if results.get(component, False) else "❌ NEEDS INSTALL"
        color = Colors.OKGREEN if results.get(component, False) else Colors.FAIL
        print(f"  {color}{status:20} {component}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Optional Components:{Colors.ENDC}")
    for component in optional:
        status = "✅ READY" if results.get(component, False) else "⚠️  NOT INSTALLED"
        color = Colors.OKGREEN if results.get(component, False) else Colors.WARNING
        print(f"  {color}{status:20} {component}{Colors.ENDC}")

    # Overall stats
    quick_wins_passed = sum(1 for c in quick_wins if results.get(c, False))
    quick_wins_total = len(quick_wins)

    optional_passed = sum(1 for c in optional if results.get(c, False))
    optional_total = len(optional)

    print(f"\n{Colors.BOLD}Overall:{Colors.ENDC}")
    print(f"  Quick Wins: {quick_wins_passed}/{quick_wins_total}")
    print(f"  Optional:   {optional_passed}/{optional_total}")

    # Verdict
    print_header("🎯 VERDICT")

    if quick_wins_passed == quick_wins_total:
        print_success("Quick Wins COMPLETE! Ready to create audiobooks! 🎉")
        print_info("\nNext steps:")
        print_info("  1. Launch UI: python ui/app.py")
        print_info("  2. Create your first audiobook")
        print_info("  3. Experience the 10x quality improvement")

        if optional_passed == 0:
            print_info("\n💡 Pro Tip: Install optional components for even more quality:")
            print_info("   Run: .\\setup_excellence.ps1 -FullStack")

    elif quick_wins_passed > 0:
        print_warning(f"Partial installation ({quick_wins_passed}/{quick_wins_total} Quick Wins ready)")
        print_info("\nTo complete installation:")
        print_info("  Run: .\\setup_excellence.ps1 -QuickWinsOnly")

    else:
        print_error("No components installed yet")
        print_info("\nTo get started:")
        print_info("  Run: .\\setup_excellence.ps1 -QuickWinsOnly")

    print("")


def main():
    """Main entry point"""
    try:
        results = run_all_tests()
        print_summary(results)

        # Exit code based on Quick Wins
        quick_wins = ['Silero VAD', 'DeepFilterNet', 'OpenVoice v2', 'Pedalboard', 'Gradio UI']
        all_quick_wins = all(results.get(c, False) for c in quick_wins)

        sys.exit(0 if all_quick_wins else 1)

    except KeyboardInterrupt:
        print_error("\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
