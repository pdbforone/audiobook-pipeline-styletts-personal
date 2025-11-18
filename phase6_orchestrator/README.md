# Audiobook Orchestrator (Advanced / Legacy CLI)
> Originally written as the commercial production runbook—now serves as the power-user companion to the Personal Audiobook Studio UI for private listening runs.

> **Current role (Nov 2025):** The Gradio UI automatically calls this orchestrator for you. Reach for these CLI commands only when you need manual control, troubleshooting, or manifest-based experiments to create personal-study audiobooks.

---

## 🎯 Quick Start
```bash
# Single book (default run: Phases 1-5)
cd phase6_orchestrator
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  /path/to/book.pdf

# Single book with subtitles
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --enable-subtitles \
  /path/to/book.pdf

# Single book with custom voice
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --voice narrator_female_01 \
  /path/to/book.pdf

# Run specific phases only (e.g., phases 4 and 5)
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --phases 4 5 \
  /path/to/book.pdf

# Batch processing (10–50 titles, legacy workflow)
cd phase7_batch
poetry run python src/phase7_batch/main.py \
  --manifest ../manifests/current_batch.csv \
  --pipeline ../pipeline.json \
  --workers 6 \
  --enable-subtitles
```

---

## ⚙️ Orchestrator CLI Options

### Required Arguments
- `input_file` — Path to source PDF/EPUB/TXT file

### Optional Flags
| Flag | Default | Description |
|------|---------|-------------|
| `--pipeline-json PATH` | `../pipeline.json` | Path to pipeline state file |
| `--phases N [N ...]` | `1 2 3 4 5` | Select which phases to run (e.g., `--phases 4 5` for TTS + enhancement only) |
| `--voice VOICE_ID` | *(auto)* | Override TTS voice selection (e.g., `narrator_female_01`, `morgan_freeman`) |
| `--max-retries N` | `2` | Maximum retry attempts for failed phases |
| `--no-resume` | *(disabled)* | Disable checkpoint/resume logic (always start fresh) |
| `--enable-subtitles` | *(disabled)* | Run Phase 5.5 subtitle generation after Phase 5 |

### Examples
```bash
# Retry-tolerant run with custom voice
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --max-retries 3 \
  --voice narrator_male_deep \
  book.pdf

# Fresh run (ignore previous state)
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --no-resume \
  book.pdf

# Re-run only TTS (Phase 4) after fixing config
poetry run python orchestrator.py \
  --pipeline-json ../pipeline.json \
  --phases 4 \
  book.pdf
```

---

## 📊 System Status
- ✅ Phases 1–5 are actively exercised through the Personal Audiobook Studio UI (this CLI simply exposes the same orchestration).
- 🟡 Subtitle generation (Phase 5.5) remains optional via `--enable-subtitles`.
- 🟠 Batch tooling (Phase 7) is still available but considered legacy/power-user territory.
- ⚠️ Phase 4 continues to lack automated tests—smoke-test XTTS/Kokoro changes manually.

---

## 🔧 Common Commands
```bash
# Inspect pipeline status for a phase
cat pipeline.json | jq '.phase5.status'

# List finished masters
ls -lh phase5_enhancement/processed/*.mp3

# Count titles currently staged
find artifacts/chunks -maxdepth 1 -type d | wc -l

# Monitor disk usage
df -h .

# Follow batch logs
tail -f phase7_batch/logs/batch_*.log
```

---

## 📁 Key Locations
```
artifacts/text/                 # Phase 2 extractions
artifacts/chunks/               # Phase 3 segments
artifacts/audio/                # Phase 4 raw WAVs
phase5_enhancement/processed/   # Final MP3 audiobooks
phase5_enhancement/subtitles/   # SRT/VTT + metrics
voice_assets/                   # Reference audio for cloning
pipeline.json                   # Master state (backup daily)
```

---

## 🚨 Troubleshooting Cheatsheet

| Symptom | Likely Cause | Quick Fix |
|---------|--------------|-----------|
| `conda: environment not found` | `phase4_tts` env missing | `cd phase4_tts && conda env create -f environment.yml` |
| Pipeline stops at Phase X | Input/format issue | Check `pipeline.json` errors, rerun orchestrator for that title |
| Out of memory during batch | Too many workers | Lower `--workers`, close apps, check `htop` |
| Subtitles drift / poor WER | Whisper model underperforming | Re-run Phase 5.5 with `--reference-text` or larger model |
| Voice mismatch | Wrong suggested voice | Override with `--voice` flag in orchestrator |

---

## 📋 Production Checklist (Personal Use)

**Before batch run**
- [ ] Confirm all titles are public domain.
- [ ] Backup `pipeline.json`.
- [ ] Ensure ≥50 GB free disk space.
- [ ] Update manifest with priorities + voice assignments.
- [ ] Close heavy applications.

**After batch run**
- [ ] Review `pipeline.json` for any failures.
- [ ] Spot-check 2–3 audiobooks (intro/mid/outro).
- [ ] Verify subtitle sync on sample title (if generated).
- [ ] Copy masters to your private listening library (phone, Plex, Audiobookshelf) and external backup.
- [ ] Skip public uploads unless you intentionally revisit the legacy publishing workflow.

**Weekly**
- [ ] Backup completed audiobooks offsite.
- [ ] Cleanup old artifacts (archive first).
- [ ] Jot down listening notes (what to re-run, which voices resonate most).
- [ ] Update manifests for next batch.

---

## 🎯 Quality Targets

| Metric | Target | Current Avg |
|--------|--------|-------------|
| Text extraction yield | > 98% | ✅ 99.1% |
| MOS (audio quality) | > 4.5 | ✅ 4.6 |
| Subtitle WER | < 15% | ✅ 12% |
| Processing time/book | < 2 hours | ✅ 1.8 hours |

---

## 📒 Personal Listening Notes to Track
- Titles processed (weekly/monthly).
- Total runtime ready for private listening.
- Average processing time per title.
- Error rates by phase.
- Favorite voices or mastering presets per genre.
- Time spent enjoying finished audiobooks while commuting/driving/exercising.

Maintain lightweight notes in `docs/personal_listening_log.md` (or reuse the existing spreadsheet if helpful).

---

## 🔐 Security & Backup
- Keep repo private; do not expose workflow publicly.
- Daily: sync `pipeline.json` to cloud storage.
- Weekly: backup `phase5_enhancement/processed/` and `subtitles/`.
- Monthly: full repo snapshot + voice assets to encrypted drive.

---

## 📚 Reference Documents
- `PROJECT_OVERVIEW.md` — Full business + technical plan.
- `phase6_orchestrator/README.md` — Orchestrator usage.
- `phase6_orchestrator/PIPELINE_JSON_SCHEMA.md` — State schema.
- `DEPENDENCY_CLEANUP_GUIDE.md` — Pruning instructions.
- `docs/publishing_checklist.md` — Upload SOP (YouTube, podcast).

---

## ⚙️ System Specs (Current Rig)
- CPU: _[fill in]_  
- RAM: _[fill in]_  
- Storage: _[fill in]_  
- OS: _[fill in]_  
- Capacity: ~20 titles/overnight batch, 50–100 per month.

Update this section when hardware changes.

---

## 💰 Legacy Business Snapshot (Historical)
- Cost per book (electricity + time): ~$2–3.
- Sweet spot: Inspiring classics, philosophy, mystery series.
- Break-even: ~100 titles (catalog effect drives exponential revenue).
- Goal: Consistent upload cadence + playlist strategy.

> Ignore unless you intentionally reboot the commercial plan—the active workflow is strictly for private listening and study.

---

**Daily operations:** run commands in Quick Start, follow checklists, and capture personal listening notes. Everything else lives in `PROJECT_OVERVIEW.md`.
Keep documenting improvements—future you (or future collaborators) will thank you.
