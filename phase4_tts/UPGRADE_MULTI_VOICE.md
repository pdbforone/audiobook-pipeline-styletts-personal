# Phase 4 Multi-Voice Upgrade Guide

**Date**: October 18, 2025  
**Goal**: Add genre-aware voice selection to Phase 4 TTS synthesis

## 🎯 What This Upgrades

Phase 4 currently uses **one reference audio** for all text. This upgrade adds:
- ✅ Multiple voice references (philosophy, fiction, memoir, etc.)
- ✅ Automatic voice selection based on Phase 3 genre detection
- ✅ Voice reference library management
- ✅ Fallback to default voice if genre not matched

## 📦 Files to Create/Modify

### New Files

1. **`configs/voice_references.json`** - Voice reference configuration
2. **`voice_references/`** - Directory for reference audio files
3. **`src/voice_manager.py`** - Voice reference management module

### Modified Files

1. **`src/main.py`** - Read Phase 3 voice selection, use appropriate reference
2. **`src/utils.py`** - Add multi-voice preparation function

---

## 🚀 Step-by-Step Setup

### Step 1: Create Voice Reference Config

Create `phase4_tts/configs/voice_references.json`:

```json
{
  "jim_locke": {
    "source_url": "https://archive.org/download/mysticism_logic_1603_librivox/mysticismandlogic_01_russell_128kb.mp3",
    "description": "Landon Elkind reading Bertrand Russell (philosophy)",
    "narrator": "Landon D. C. Elkind (male, analytic philosophy)",
    "trim_start": 10,
    "trim_end": 30,
    "preferred_profiles": ["philosophy", "academic"],
    "characteristics": {
      "pace": "measured",
      "tone": "scholarly",
      "accent": "American"
    }
  },
  "female_calm": {
    "source_url": "https://archive.org/download/pride_and_prejudice_librivox/prideandprejudice_01-03_austen.mp3",
    "description": "Kara Shallenberg reading Jane Austen (fiction)",
    "narrator": "Kara Shallenberg (female, fiction)",
    "trim_start": 60,
    "trim_end": 80,
    "preferred_profiles": ["fiction", "memoir"],
    "characteristics": {
      "pace": "natural",
      "tone": "warm",
      "accent": "American"
    }
  },
  "neutral_narrator": {
    "source_url": "https://www.archive.org/download/roughing_it_jg/rough_09_twain.mp3",
    "description": "Current default (Mark Twain reading)",
    "narrator": "Unknown (male, general)",
    "trim_start": 0,
    "trim_end": 20,
    "preferred_profiles": ["technical", "auto"],
    "characteristics": {
      "pace": "steady",
      "tone": "neutral",
      "accent": "American"
    }
  },
  "male_warm": {
    "source_url": "https://archive.org/download/toadog_1111_librivox/toadog_chapman_rg_64kb.mp3",
    "description": "Placeholder - need better source",
    "narrator": "TBD (male, warm)",
    "trim_start": 0,
    "trim_end": 20,
    "preferred_profiles": ["memoir"],
    "characteristics": {
      "pace": "comfortable",
      "tone": "friendly",
      "accent": "American"
    }
  }
}
```

### Step 2: Create Voice Manager Module

Create `phase4_tts/src/voice_manager.py`:

```python
"""
Voice Reference Manager for Phase 4 TTS

Handles:
- Downloading and preparing voice references
- Mapping voice IDs to reference audio files
- Reading Phase 3 voice selections
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import librosa
import requests
import torch
import torchaudio as ta

logger = logging.getLogger(__name__)


class VoiceReferenceManager:
    """Manages voice reference audio files for TTS cloning."""
    
    def __init__(
        self,
        config_path: str = "configs/voice_references.json",
        refs_dir: str = "voice_references",
        sample_rate: int = 24000
    ):
        self.config_path = Path(config_path)
        self.refs_dir = Path(refs_dir)
        self.sample_rate = sample_rate
        self.voice_config = {}
        self.prepared_refs = {}
        
        # Create refs directory
        self.refs_dir.mkdir(exist_ok=True)
        
        # Load config
        self._load_config()
    
    def _load_config(self):
        """Load voice reference configuration."""
        try:
            with open(self.config_path, 'r') as f:
                self.voice_config = json.load(f)
            logger.info(f"Loaded {len(self.voice_config)} voice configurations")
        except FileNotFoundError:
            logger.error(f"Voice config not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in voice config: {e}")
            raise
    
    def prepare_all_references(self, force_download: bool = False):
        """
        Prepare all voice references from config.
        
        Args:
            force_download: Re-download even if files exist
        """
        for voice_id, config in self.voice_config.items():
            self.prepare_reference(voice_id, force_download)
    
    def prepare_reference(
        self,
        voice_id: str,
        force_download: bool = False
    ) -> str:
        """
        Prepare a single voice reference.
        
        Args:
            voice_id: Voice identifier (e.g., 'jim_locke')
            force_download: Re-download even if file exists
            
        Returns:
            Path to prepared reference audio
        """
        if voice_id not in self.voice_config:
            raise ValueError(f"Unknown voice ID: {voice_id}")
        
        config = self.voice_config[voice_id]
        output_path = self.refs_dir / f"{voice_id}.wav"
        
        # Skip if already prepared
        if output_path.exists() and not force_download:
            logger.info(f"Using existing reference: {voice_id}")
            self.prepared_refs[voice_id] = str(output_path)
            return str(output_path)
        
        logger.info(f"Preparing reference for {voice_id}...")
        logger.info(f"  Source: {config['description']}")
        
        try:
            # Download MP3
            mp3_path = self.refs_dir / f"temp_{voice_id}.mp3"
            response = requests.get(config['source_url'], timeout=30)
            response.raise_for_status()
            
            with open(mp3_path, 'wb') as f:
                f.write(response.content)
            
            # Load audio
            y, sr = librosa.load(str(mp3_path), sr=None, mono=True)
            
            # Trim to specified range
            trim_start = config.get('trim_start', 0)
            trim_end = config.get('trim_end', 20)
            
            start_sample = int(trim_start * sr)
            end_sample = int(trim_end * sr)
            y_trimmed = y[start_sample:end_sample]
            
            # Verify length
            duration = len(y_trimmed) / sr
            if duration < 5:
                logger.warning(f"Reference too short: {duration:.1f}s (recommend 10-20s)")
            elif duration > 25:
                logger.warning(f"Reference too long: {duration:.1f}s (trimming to 20s)")
                y_trimmed = y_trimmed[:int(20 * sr)]
            
            logger.info(f"  Duration: {len(y_trimmed)/sr:.1f}s")
            
            # Normalize and resample
            y_norm = librosa.util.normalize(y_trimmed)
            y_resampled = librosa.resample(
                y_norm,
                orig_sr=sr,
                target_sr=self.sample_rate
            )
            
            # Save
            ta.save(
                str(output_path),
                torch.tensor(y_resampled).unsqueeze(0),
                self.sample_rate
            )
            
            # Cleanup
            mp3_path.unlink()
            
            self.prepared_refs[voice_id] = str(output_path)
            logger.info(f"✅ Prepared {voice_id}: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Failed to prepare {voice_id}: {e}")
            raise
    
    def get_reference(self, voice_id: str) -> str:
        """
        Get path to prepared reference for a voice.
        
        Args:
            voice_id: Voice identifier
            
        Returns:
            Path to reference WAV file
        """
        if voice_id not in self.prepared_refs:
            return self.prepare_reference(voice_id)
        
        return self.prepared_refs[voice_id]
    
    def get_voice_from_phase3(
        self,
        pipeline_json_path: str,
        file_id: str
    ) -> str:
        """
        Read suggested voice from Phase 3 output.
        
        Args:
            pipeline_json_path: Path to pipeline.json
            file_id: File identifier
            
        Returns:
            Voice ID (defaults to 'neutral_narrator' if not found)
        """
        try:
            with open(pipeline_json_path, 'r') as f:
                data = json.load(f)
            
            phase3_data = data.get("phase3", {}).get("files", {}).get(file_id, {})
            suggested_voice = phase3_data.get("suggested_voice", "neutral_narrator")
            
            logger.info(f"Phase 3 suggested voice: {suggested_voice}")
            
            # Verify voice exists in config
            if suggested_voice not in self.voice_config:
                logger.warning(
                    f"Voice '{suggested_voice}' not in config, "
                    f"using 'neutral_narrator'"
                )
                return "neutral_narrator"
            
            return suggested_voice
            
        except Exception as e:
            logger.warning(f"Could not read Phase 3 voice selection: {e}")
            return "neutral_narrator"
    
    def list_voices(self) -> Dict[str, str]:
        """Get list of available voices with descriptions."""
        return {
            voice_id: config['description']
            for voice_id, config in self.voice_config.items()
        }
```

### Step 3: Update main.py

Replace the voice reference preparation section in `src/main.py`:

```python
# OLD CODE (around line 50):
# ref_path = prepare_reference_audio(config)

# NEW CODE:
from voice_manager import VoiceReferenceManager

# Initialize voice manager
voice_mgr = VoiceReferenceManager(
    config_path="../configs/voice_references.json",
    sample_rate=config.sample_rate
)

# Prepare all references (or just download on-demand)
logger.info("Preparing voice references...")
voice_mgr.prepare_all_references()

# Get voice selection from Phase 3
suggested_voice = voice_mgr.get_voice_from_phase3(
    str(json_path),
    args.file_id
)

# Get appropriate reference
ref_path = voice_mgr.get_reference(suggested_voice)
logger.info(f"Using voice: {suggested_voice} ({ref_path})")
```

---

## 🧪 Testing

### Test 1: Verify Voice References Prepare Correctly

```powershell
cd phase4_tts

# Test voice manager
poetry run python -c "
from src.voice_manager import VoiceReferenceManager

mgr = VoiceReferenceManager(config_path='configs/voice_references.json')
print('Available voices:', mgr.list_voices())

# Prepare all references
mgr.prepare_all_references()
print('✅ All references prepared')
"
```

**Expected output**:
```
Available voices: {
  'jim_locke': 'Landon Elkind reading Bertrand Russell (philosophy)',
  'female_calm': 'Kara Shallenberg reading Jane Austen (fiction)',
  ...
}
Preparing reference for jim_locke...
  Duration: 18.5s
✅ Prepared jim_locke: voice_references/jim_locke.wav
...
```

### Test 2: Verify Phase 3 Voice Reading

```powershell
# Assuming you ran Phase 3 on The Analects
poetry run python -c "
from src.voice_manager import VoiceReferenceManager

mgr = VoiceReferenceManager(config_path='configs/voice_references.json')
voice = mgr.get_voice_from_phase3('../pipeline.json', 'analects_test_v2')
print(f'Selected voice: {voice}')
print(f'Reference path: {mgr.get_reference(voice)}')
"
```

**Expected output**:
```
Phase 3 suggested voice: neutral_narrator
Selected voice: neutral_narrator
Reference path: voice_references/neutral_narrator.wav
```

### Test 3: Full TTS with Voice Selection

```powershell
# Run Phase 4 on first chunk
poetry run python src/main.py `
  --file_id analects_test_v2 `
  --chunk_id 0 `
  --json_path ../pipeline.json
```

**Check**:
- Should use `neutral_narrator` reference (since Analects used 'auto' profile)
- Audio should sound like the Mark Twain narrator (current default)

---

## 🎯 Next Steps

### 1. **Find Better Reference Audio** (This Weekend)

The current references are placeholders. Find better LibriVox samples:

**Philosophy (jim_locke)**:
- ✅ Current: Landon Elkind (Russell) - Good!
- 🔍 Alternative: David Barnes reading philosophy (British accent)

**Fiction (female_calm)**:
- ⚠️ Current: Kara Shallenberg (Austen) - May not be ideal
- 🔍 Better: Ruth Golding or Bella Bolster (check LibriVox for full readings)

**Memoir (male_warm)**:
- ❌ Current: Placeholder
- 🔍 Find: Warm male narrator reading memoir/biography

**How to find**:
1. Browse LibriVox by genre: https://librivox.org/search
2. Listen to samples
3. Find full-length readings (not just chapters)
4. Download MP3, identify best 10-20s segment
5. Update `voice_references.json` with URL and trim times

### 2. **Test on Different Genres** (Next Week)

Process different text types through full pipeline:
- Philosophy text → Should use `jim_locke`
- Fiction text → Should use `female_calm`
- Memoir text → Should use `male_warm`

### 3. **Fine-Tune Voice Parameters** (Optional)

Adjust Chatterbox parameters per voice in config:
```json
"jim_locke": {
  ...
  "tts_params": {
    "exaggeration": 0.3,  // Less dramatic for philosophy
    "cfg_weight": 0.6,    // More stable pacing
    "temperature": 0.6    // More consistent
  }
}
```

---

## 🐛 Troubleshooting

**Issue**: `FileNotFoundError: voice_references.json`

**Fix**: Create `phase4_tts/configs/` directory and add the JSON file

---

**Issue**: Download fails for reference audio

**Fix**: 
1. Manually download MP3 from URL
2. Place in `voice_references/`
3. Run preparation script

---

**Issue**: "Voice 'jim_locke' not in config"

**Fix**: Ensure `configs/voice_references.json` includes all voices from Phase 3's `configs/voices.json`

---

## 📊 Expected Results

After upgrade:

| Text Genre | Phase 3 Profile | Phase 3 Voice | Phase 4 Reference |
|-----------|----------------|---------------|-------------------|
| Philosophy | philosophy | jim_locke | Russell reading (measured) |
| Fiction | fiction | female_calm | Austen reading (warm) |
| Memoir | memoir | male_warm | TBD (friendly) |
| Technical | technical | neutral_narrator | Twain (default) |
| Auto | auto | neutral_narrator | Twain (default) |

---

## ✅ Upgrade Complete When

- [ ] `configs/voice_references.json` created
- [ ] `src/voice_manager.py` created
- [ ] `src/main.py` updated to use voice manager
- [ ] All 4 voice references downloaded and prepared
- [ ] Test: Voice manager lists all voices
- [ ] Test: Can read Phase 3 voice selection
- [ ] Test: TTS synthesis uses correct voice
- [ ] Phase 4 works end-to-end with genre-aware voices

**Time estimate**: 2-3 hours
