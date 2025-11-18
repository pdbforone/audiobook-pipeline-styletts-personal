# Droid (Astromech) Voice & Beep/Boop Effects Guide

**Last Updated:** November 2025  \
**Scope:** Phase 4 (TTS synthesis) optional sound-design layer  \
**Audience:** Developers and sound designers experimenting with non-verbal robot or "droid"/“astromech” style outputs inside the Personal Audiobook Studio.

---

## 1. Why This Exists
While the Studio focuses on natural narration, some experiments (promo clips, UI feedback, easter eggs) call for R2-D2 style beeps and boops instead of speech. This guide captures research-backed approaches that stay local, royalty-free, and compatible with the existing Python toolchain.

---

## 2. Library Options (Free & Personal-Use Friendly)
| Approach | Platforms | Pros | Considerations |
|----------|-----------|------|----------------|
| `ttastromech` | macOS, Linux | Purpose-built Astromech (R2-D2) sound generator with pre-sequenced tones. Drop-in CLI/py usage. | Not available on Windows; depends on system audio players (`afplay`, `play`). Keep outputs private unless you re-confirm the license. |
| `PyAudio` (PortAudio) | Windows, macOS, Linux | Cross-platform audio stream access. Fully programmatic sine-wave synthesis so you control mapping and effects. | Requires PortAudio backend; you own tone design + playback loop. |
| `pyo` | Windows, macOS, Linux | Advanced synthesis (FM, filters) for richer effects. | Heavier dependency; run a background server. Review licensing if you later distribute beyond personal study. |
| Pure Python + WAV export (`wave`, `numpy`) | All | Zero external deps beyond stdlib + NumPy. | Needs external player (e.g., `aplay`) and pre-rendering. |

> **Recommendation:** Start with `ttastromech` on macOS/Linux for fast iteration. For Windows or finer control, build directly on `PyAudio`. Both options align with the private-study charter; re-check licensing before public sharing.

---

## 3. Installation Cheatsheet
```bash
# macOS / Linux quick start
pip install ttastromech

# Cross-platform fallback
pip install pyaudio numpy
# (Windows) Ensure PortAudio binaries are available or install via pip wheel `pip install pipwin && pipwin install pyaudio`
```

---

## 4. Mapping Text to Droid Speech
1. **Tokenize text** into characters or syllables.
2. **Assign tone parameters** per token:
   - Frequency: random 200–2,000 Hz (bias vowels/lowercase to softer ranges).
   - Duration: 50–200 ms per tone.
   - Envelope: quick attack (5 ms) + exponential decay to avoid harsh clicks.
3. **Sequence** tones with 20–40 ms silences to add rhythm.
4. **Playback** immediately (PyAudio stream) or pre-render WAV for reuse.
5. **Randomize** occasional trills (rapid arpeggios) for "question" inflection.

---

## 5. PyAudio Reference Implementation
```python
import math
import random
import struct
import time

import numpy as np
import pyaudio

SAMPLE_RATE = 44100
BIT_DEPTH = 16
CHANNELS = 1
DURATION_RANGE = (0.05, 0.2)   # seconds
FREQ_RANGE = (200, 2000)       # Hz
PAUSE_RANGE = (0.02, 0.04)     # seconds

def _tone(freq: float, duration: float) -> bytes:
    samples = np.arange(int(duration * SAMPLE_RATE))
    waveform = np.sin(2 * math.pi * freq * samples / SAMPLE_RATE)
    envelope = np.linspace(1.0, 0.0, waveform.size)
    data = waveform * envelope
    return b"".join(
        struct.pack("<h", int(sample * 32767)) for sample in data
    )

def speak_droid(text: str) -> None:
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=CHANNELS, rate=SAMPLE_RATE, output=True)
    try:
        for char in text:
            freq = random.uniform(*FREQ_RANGE)
            duration = random.uniform(*DURATION_RANGE)
            stream.write(_tone(freq, duration))
            time.sleep(random.uniform(*PAUSE_RANGE))
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

if __name__ == "__main__":
    speak_droid("Incoming transmission acknowledged.")
```

---

## 6. Integration Tips
- **UI Hooks:** Trigger quick beeps for button confirmations or background render progress.
- **TTS Hook:** Register a special `voice_id="droid_fx"` that routes Phase 4 chunks through the PyAudio path above instead of XTTS.
- **Asset Export:** Capture PyAudio output via `soundfile` to store WAV assets if you need to stitch them into audiobooks.
- **Random Seeds:** Allow deterministic seeds for repeatable sequences when QAing.
- **Testing:** Add smoke tests ensuring the `droid_fx` voice path simply emits non-empty audio buffers without blocking.

### Notification Beeps (Ready-to-Use “Astromech” Set)
- Generated CPU-safe WAVs live at `assets/notifications/droid_success.wav` and `assets/notifications/droid_alert.wav` (NumPy + soundfile synthesis; no extra deps).
- Suggested mapping:
  - `droid_success.wav` → job completion, UI confirm.
  - `droid_alert.wav` → failure/attention needed.
- Playback example (Python):
  ```python
  import soundfile as sf, sounddevice as sd, pathlib
  beep = pathlib.Path("assets/notifications/droid_success.wav")
  audio, sr = sf.read(beep)
  sd.play(audio, sr); sd.wait()
  ```
  If `sounddevice` isn’t installed, any media player works; keep paths relative to repo root.

---

## 7. Troubleshooting
| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| No audio playback | PortAudio backend missing | Install platform packages (`brew install portaudio`, `apt install portaudio19-dev`). |
| Audio clicks/pops | Missing envelope or too-short buffers | Apply short attack/decay envelope and keep tone buffers ≥ 10 ms. |
| Windows install fails | Missing wheel | Use `pipwin install pyaudio` or download prebuilt wheels. |
| Sounds too repetitive | Not enough randomness | Expand frequency/duration range and add multi-tone flourishes. |

---

## 8. Next Steps
- Prototype a `phase4_tts.engines.droid_fx` module that implements the voice adapter contract.
- Add a Gradio UI toggle to preview droid beeps for fun/promotional outputs.
- Document licensing (note which dependencies are MIT/LGPL vs. personal-use-only) and keep the resulting sounds inside the private listening workflow unless you re-evaluate terms for distribution.

