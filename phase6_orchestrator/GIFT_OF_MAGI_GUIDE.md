# 🎄 Gift of the Magi - Pipeline Test Guide

## Quick Start

### Option 1: Fresh Run (No Resume)
```batch
cd phase6_orchestrator
.\test_gift_of_magi.bat
```

**What it does:**
- Runs all 5 phases from scratch
- Uses separate pipeline file: `pipeline_magi.json`
- Fresh start even if you ran it before

**Time estimate:** 5-15 minutes (depending on TTS)

---

### Option 2: Resume-Enabled Run (Recommended)
```batch
cd phase6_orchestrator
.\run_gift_of_magi.bat
```

**What it does:**
- Runs all 5 phases
- Can resume if interrupted
- Skips completed phases automatically

**Time estimate:** 5-15 minutes first run, instant if resuming

---

## What to Expect

### Phase 1: Validation (~5 seconds)
```
✓ File integrity verified
✓ PDF classified as text-based
✓ Metadata extracted
```

### Phase 2: Text Extraction (~30 seconds)
```
✓ Text extracted from PDF
✓ Quality checks passed
✓ Saved to: phase2-extraction/extracted_text/Gift_of_the_Magi.txt
```

### Phase 3: Chunking (~10 seconds)
```
✓ 8-12 chunks created (estimated for this story)
✓ Average coherence: >0.4
✓ All chunks within duration limits
✓ Saved to: phase3-chunking/chunks/
```

### Phase 4: TTS Synthesis (5-10 minutes)
```
Synthesizing 8-12 chunks...
[Progress bar]
✓ All chunks synthesized
✓ Saved to: phase4_tts/audio_chunks/
```

**Note**: This is the longest phase. Be patient!

### Phase 5: Enhancement (~30 seconds)
```
✓ Noise reduction applied
✓ Loudness normalized
✓ Chunks stitched together
✓ Final audiobook: phase5_enhancement/output/audiobook.mp3
```

---

## Expected Output

### File Structure After Success:
```
audiobook-pipeline-styletts-personal/
├── pipeline_magi.json              # Pipeline state
├── input/
│   └── Gift of the Magi.pdf        # Original PDF
├── phase2-extraction/
│   └── extracted_text/
│       └── Gift_of_the_Magi.txt    # Extracted text
├── phase3-chunking/
│   └── chunks/
│       ├── Gift_of_the_Magi_chunk_001.txt
│       ├── Gift_of_the_Magi_chunk_002.txt
│       └── ...
├── phase4_tts/
│   └── audio_chunks/
│       ├── Gift_of_the_Magi_chunk_001.wav
│       ├── Gift_of_the_Magi_chunk_002.wav
│       └── ...
└── phase5_enhancement/
    └── output/
        └── audiobook.mp3           # 🎧 FINAL AUDIOBOOK!
```

---

## Story Details

**Title**: "The Gift of the Magi"  
**Author**: O. Henry  
**Length**: ~2,000 words  
**Reading Time**: ~10-15 minutes  
**Complexity**: Simple narrative, good for testing

---

## Quality Metrics to Check

After completion, check `pipeline_magi.json` for:

### Phase 3 Metrics:
- `avg_coherence`: Should be >0.4
- `avg_flesch`: Should be >60
- `chunks_exceeding_duration`: Should be 0
- `chunks_in_target_range`: Should equal total chunks

### Phase 4 Metrics:
- `avg_mos`: Should be >4.0 (quality score)
- `avg_snr`: Should be >15dB
- `total_chunks`: Should match Phase 3

### Phase 5 Metrics:
- `final_loudness`: Should be ~-23 LUFS
- `snr_improvement`: Should be positive
- `chunk_count`: Should match previous phases

---

## Troubleshooting

### Phase 1 Fails
**Error**: "File not found" or "Corrupt PDF"
**Fix**: Verify PDF is readable:
```batch
start "" "input\Gift of the Magi.pdf"
```

### Phase 2 Fails
**Error**: "No text extracted"
**Fix**: Check if PDF is text-based (not scanned image)

### Phase 3 Fails
**Error**: "No chunks created"
**Fix**: Verify Phase 2 extracted text successfully

### Phase 4 Fails
**Error**: "Conda environment not found"
**Fix**: Create chatterbox_env:
```batch
cd phase4_tts
conda env create -f environment.yml
```

### Phase 5 Fails
**Error**: "No audio chunks found"
**Fix**: Verify Phase 4 completed successfully

---

## Manual Check Points

### After Phase 2:
```batch
type phase2-extraction\extracted_text\Gift_of_the_Magi.txt | more
```
Should show the story text.

### After Phase 3:
```batch
dir phase3-chunking\chunks\Gift_of_the_Magi*
```
Should show 8-12 .txt files.

### After Phase 4:
```batch
dir phase4_tts\audio_chunks\Gift_of_the_Magi*
```
Should show 8-12 .wav files.

### After Phase 5:
```batch
dir phase5_enhancement\output\audiobook.mp3
```
Should exist and be >1MB.

**Listen to it:**
```batch
start "" "phase5_enhancement\output\audiobook.mp3"
```

---

## Performance Benchmarks

**On typical hardware:**
- Phase 1: 5s
- Phase 2: 30s
- Phase 3: 10s
- Phase 4: 5-10 minutes (depends on CPU)
- Phase 5: 30s

**Total**: 6-11 minutes

---

## Resume from Checkpoint

If interrupted, just re-run:
```batch
.\run_gift_of_magi.bat
```

The orchestrator will:
1. Check `pipeline_magi.json`
2. Skip completed phases
3. Resume from where it stopped

---

## Clean Start

To run fresh (delete all outputs):
```batch
del pipeline_magi.json
rd /s /q phase2-extraction\extracted_text\Gift_of_the_Magi.txt
rd /s /q phase3-chunking\chunks\Gift_of_the_Magi*
rd /s /q phase4_tts\audio_chunks\Gift_of_the_Magi*
rd /s /q phase5_enhancement\output\audiobook.mp3
rd /s /q phase5_enhancement\processed\Gift_of_the_Magi*
```

Then run again:
```batch
.\test_gift_of_magi.bat
```

---

## Success Criteria

Pipeline succeeds when:
1. ✅ All phases show status: "success"
2. ✅ `audiobook.mp3` exists and plays
3. ✅ No "failed" status in `pipeline_magi.json`
4. ✅ Chunk counts match across phases 3, 4, 5
5. ✅ Audio quality sounds good (no truncation, no garbling)

---

## Next Steps After Success

1. **Listen to the audiobook** - Verify quality
2. **Check metrics** - Review `pipeline_magi.json`
3. **Test with longer book** - Try a full chapter or book
4. **Adjust settings** - Tweak chunk sizes if needed
5. **Scale up** - Process multiple files with Phase 7 (batch)

---

## Advanced: Command-Line Options

### Run specific phases only:
```batch
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --phases 3 4
```

### Increase retry attempts:
```batch
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --max-retries 5
```

### Disable resume:
```batch
python phase6_orchestrator\orchestrator.py "input\Gift of the Magi.pdf" --no-resume
```

---

## Files Created for You

**Test Scripts:**
- `test_gift_of_magi.bat` - Fresh run, no resume
- `run_gift_of_magi.bat` - Resume-enabled (recommended)

**Documentation:**
- `GIFT_OF_MAGI_GUIDE.md` - This file
- `QUICK_START.md` - General guide
- `TROUBLESHOOTING.md` - Detailed help

---

## Tips for Success

1. **Be patient with Phase 4** - TTS synthesis takes time
2. **Don't interrupt Phase 4** - Let chunks complete
3. **Check logs** - They're detailed and helpful
4. **Use resume** - If something fails, fix and re-run
5. **Verify outputs** - Listen to a few chunks after Phase 4

---

**Ready?** Run this:
```batch
cd phase6_orchestrator
.\run_gift_of_magi.bat
```

---

**Last Updated**: 2025-10-11  
**Test File**: Gift of the Magi.pdf (86KB, ~2000 words)  
**Expected Time**: 6-11 minutes  
**Expected Output**: ~10-15 minute audiobook

