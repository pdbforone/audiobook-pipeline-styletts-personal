# Audiobook Production Pipeline (Private)
> Internal operations manual for commercial audiobook production. Keep repository private.

---

## 🎯 Quick Start
```bash
# Single book (default run)
cd phase6_orchestrator
poetry run python orchestrator.py \
  --pipeline ../pipeline.json \
  /path/to/book.pdf

# Single book with subtitles
poetry run python orchestrator.py \
  --pipeline ../pipeline.json \
  --enable-subtitles \
  /path/to/book.pdf

# Batch processing (10–50 titles)
cd phase7_batch
poetry run python src/phase7_batch/main.py \
  --manifest ../manifests/current_batch.csv \
  --pipeline ../pipeline.json \
  --workers 6 \
  --enable-subtitles
```

---

## 📊 System Status
- ✅ Phases 1–7 production-ready
- ✅ Subtitle generation (Phase 5.5) integrated
- ✅ Batch processing stable
- ⚠️ Phase 4 lacks automated tests (monitor manually)

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

## 📋 Production Checklist

**Before batch run**
- [ ] Confirm all titles are public domain.
- [ ] Backup `pipeline.json`.
- [ ] Ensure ≥50 GB free disk space.
- [ ] Update manifest with priorities + voice assignments.
- [ ] Close heavy applications.

**After batch run**
- [ ] Review `pipeline.json` for any failures.
- [ ] Spot-check 2–3 audiobooks (intro/mid/outro).
- [ ] Verify subtitle sync on sample title.
- [ ] Copy masters to publishing queue + external backup.
- [ ] Upload to YouTube/podcast platforms.

**Weekly**
- [ ] Backup completed audiobooks offsite.
- [ ] Cleanup old artifacts (archive first).
- [ ] Log analytics (views, RPM, downloads).
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

## 📈 Production Metrics to Track
- Titles processed (weekly/monthly).
- Total runtime published (hours).
- Average processing time per title.
- Error rates by phase.
- YouTube views + revenue per title.
- Podcast downloads + CPM.

Maintain spreadsheet in `docs/production_log.xlsx`.

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

## 💰 Business Snapshot
- Cost per book (electricity + time): ~$2–3.
- Sweet spot: Inspiring classics, philosophy, mystery series.
- Break-even: ~100 titles (catalog effect drives exponential revenue).
- Goal: Consistent upload cadence + playlist strategy.

---

**Daily operations:** run commands in Quick Start, follow checklists, update logs. Everything else lives in `PROJECT_OVERVIEW.md`.  
Keep documenting improvements—future you (or future collaborators) will thank you.
