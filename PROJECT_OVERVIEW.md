# Project Overview · Private Audiobook Production System

> **Audience:** Owner, trusted collaborators, and future team members.  
> **Purpose:** Capture business logic, technical architecture, and operating playbook for a fully automated, commercial audiobook pipeline.  
> **Security:** This document is **PRIVATE**. Do not distribute publicly.

---

## 1. Business Model

### 1.1 Mission Statement
Build and operate a lean audiobook publishing studio that:
- Converts public domain texts into commercial-grade assets.
- Delivers consistent narrator branding via voice cloning.
- Publishes to multiple revenue channels with minimal manual labor.
- Scales to 50–100+ titles per month using automation and CPU-only infrastructure.

### 1.2 Revenue Streams
| Channel | Description | Notes |
|---------|-------------|-------|
| **YouTube** | Ad revenue, memberships, Super Thanks | Primary funnel; benefits from subtitles + playlists. |
| **Podcasts** | Host-read sponsorships, dynamic ad insertion | Use podcast networks (Podbean, Anchor, Captivate). |
| **Streaming (Future)** | Audible, Spotify Audiobooks, Storytel | Requires QC + platform-specific packaging. |
| **Subscription (Future)** | Patreon, private RSS, direct sales bundles | Leverage loyal audience after catalog growth. |

### 1.3 Unit Economics (Per Audiobook)
| Item | Cost | Notes |
|------|------|-------|
| Content acquisition | **$0** | Public domain texts only. |
| Software licensing | **$0** | Exclusively free & open-source stack. |
| Hardware amortization | ~$1.50 | Consumer PC (~$1500 over 1,000 titles). |
| Electricity | ~$0.50–$1.00 | Depends on runtime (~2 hrs/book) and rates. |
| Labor | ≤$1 (oversight) | Most time spent vetting sources + QC. |
| **Total** | **≈$3 per book** | Payback < 3 months once catalog monetizes. |

### 1.4 Competitive Advantages
- **Marginal cost ≈ $0.** After initial setup, each additional book is nearly free.
- **Consistent voice identity.** Voice cloning ensures brand recognition across series.
- **Automated QA.** Validation layers catch OCR issues, TTS artifacts, and subtitle drift.
- **Multi-format output.** Single run yields audio masters, subtitles, and video assets.
- **Batch throughput.** Parallel processing handles 10–50 books per batch run.

---

## 2. System Architecture

Seven primary phases (plus 5.5) comprise the pipeline. Each phase is isolated via Poetry environments (Conda for Phase 4 only) to maintain reproducibility and minimize dependency conflicts. All state flows through `pipeline.json`.

### 2.1 Phase Overview
| Phase | Description | Key Tools | Status |
|-------|-------------|-----------|--------|
| **1. Validation & Repair** | Verifies integrity, repairs common PDF/EPUB issues, extracts metadata. | `pikepdf`, `PyMuPDF`, `hachoir`, `pydantic` | ✅ Production-ready |
| **2. Text Extraction** | Multi-format ingest, OCR when needed, text normalization. | `pdfplumber`, `pytesseract`, `ftfy`, `langdetect` | ✅ Production-ready |
| **3. Semantic Chunking** | Genre-aware segmentation, readability scoring, voice suggestion. | `spaCy`, `sentence-transformers`, `textstat` | ✅ Production-ready |
| **4. TTS Synthesis** | Voice cloning with validation + retries. | Chatterbox TTS Extended, `torchaudio`, Whisper tier 2 validation | ✅ Production-ready (expand tests) |
| **5. Audio Enhancement** | Noise reduction, LUFS normalization, crossfades, mastering. | `librosa`, `pyloudnorm`, `pydub`, `numpy` | ✅ Production-ready |
| **5.5. Subtitle Generation** | CPU Whisper transcription, SRT/VTT generation, WER metrics. | `faster-whisper`, `jiwer`, `webvtt-py`, `srt` | ✅ Production-ready |
| **6. Orchestration** | Single-title runner with resume + reporting. | `rich`, `typer`, JSON state machine | ✅ Production-ready |
| **7. Batch Processing** | Parallel execution, queue management, resource throttling. | `concurrent.futures`, `psutil` | ✅ Production-ready |

### 2.2 Supporting Services
- **Pipeline State:** `pipeline.json` (see schema reference) tracks metrics, artifacts, and error states. Always back up before and after large batches.
- **Voice Library:** `phase4_tts/voice_references/` contains curated reference audio. Maintain consistent 10–20 second clips.
- **Artifacts:** Each phase writes to `artifacts/` for traceability (text, chunks, raw audio, processed masters).

---

## 3. Production Workflow

### 3.1 Step-by-Step Overview
1. **Source Selection**
   - Maintain a shortlist spreadsheet (title, source URL, public domain proof, notes).
   - Prioritize classics or thematic bundles (e.g., “Stoic Philosophy Series”).
2. **Intake & Validation**
   - Download source into `input/`.
   - Run Phase 1 manually if necessary to vet unusual formats.
3. **Batch Execution**
   - Use Phase 7 for volume; fall back to Phase 6 for single titles or troubleshooting.
4. **Quality Control**
   - Inspect `pipeline.json` for anomalies.
   - Spot-check audio (intro, random middle chapter, conclusion).
   - Confirm subtitle sync with `ffplay` or VLC.
5. **Distribution Prep**
   - Generate cover art or reuse template (dimensions: 1920×1080 for YT, 3000×3000 for podcasts).
   - Export MP4 (audio + static cover + subtitles) via FFmpeg helper script.
6. **Publishing & Monetization**
   - Upload to YouTube (include timestamps, keywords, public domain notice).
   - Push audio to podcast host (include show notes, call-to-action).
   - Schedule social posts or community updates.
7. **Analytics & Iteration**
   - Log KPIs (views, CPM, subscriber growth) weekly.
   - Use insights to prioritize sequel titles or extended bundles.

### 3.2 Sample Batch Command
```bash
cd phase7_batch
poetry run python src/phase7_batch/main.py \
  --manifest manifests/q2_classics.csv \
  --pipeline ../pipeline.json \
  --workers 6 \
  --enable-subtitles
```

Manifest columns: `file_id,input_path,voice_id,priority`.

---

## 4. Quality Standards

### 4.1 Extraction
- **Yield:** > 98% of text content recovered.
- **Gibberish:** < 2% flagged by heuristics.
- **Language confidence:** > 0.90 average.

### 4.2 Audio
- **MOS proxy:** ≥ 4.5 (via spectral centroid heuristic).
- **SNR improvement:** ≥ +5 dB post-processing.
- **Loudness:** –23 LUFS ±2 dB (podcast standard).
- **Consistency:** No mid-sentence splits or voice dropouts.

### 4.3 Subtitles
- **Coverage:** ≥ 95% of total runtime.
- **WER:** ≤ 15% (Whisper “small” model baseline).
- **Timing drift:** ≤ 2 seconds at heads/tails.

### 4.4 Throughput
- **Single title:** ~2 hours end-to-end.
- **Batch of 20:** ~6–8 hours (depends on CPU + I/O).

---

## 5. File Organization

```
audiobook-pipeline/
├── input/                       # Raw source files
├── artifacts/
│   ├── text/                    # Phase 2 extractions
│   ├── chunks/                  # Phase 3 outputs
│   ├── audio/                   # Phase 4 per-chunk WAVs
│   └── processed/               # Phase 5 mastered chunks
├── phase5_enhancement/
│   ├── processed/               # Final MP3 masters
│   └── subtitles/               # SRT/VTT + metrics JSON
├── voice_assets/                # Reference samples, narrator branding
├── docs/                        # Internal documentation (this file, SOPs)
├── manifests/                   # Batch manifest CSVs
├── scripts/                     # Operational utilities (render_video, backups)
└── pipeline.json                # Master state file (CRITICAL)
```

> ⚠️ **Reminder:** `pipeline.json` must be backed up daily. Losing this file means losing run history, QA metrics, and resume capability.

---

## 6. System Requirements

### 6.1 Hardware Baseline
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 6 cores / 12 threads | 12–16 cores (Ryzen 9 / i9) |
| RAM | 16 GB | 32 GB |
| Storage | 1 TB SSD | 2 TB NVMe (plus external backup) |
| OS | Windows 10/11, macOS, or Linux | Linux or Windows with WSL2 for scripting |

**GPU:** Not required; all workloads are CPU-optimized.

### 6.2 Software
- Python 3.10+ (pinned for compatibility).
- Poetry (per-phase virtualenvs).
- Conda (Phase 4 environment `phase4_tts`).
- FFmpeg (video rendering/post).
- `jq`, `htop`, `df` etc. for system monitoring.

---

## 7. Cost Analysis

### 7.1 Setup Costs
| Category | Amount |
|----------|--------|
| Hardware (PC + peripherals) | $1,500 |
| Optional backup NAS / external SSD | $200–$400 |
| Branding (templates, cover design) | $100–$300 |
| **Total Initial Investment** | **$1,800–$2,200** |

### 7.2 Operating Costs
| Category | Monthly |
|----------|---------|
| Electricity | $20–$30 (based on overnight processing) |
| Cloud storage/backups | $10–$20 (optional) |
| Domain/hosting (if using website) | $10–$20 |
| Labor (oversight) | Variable (~5–10 hrs/week) |

### 7.3 Revenue Targets
- **YouTube:** Expect $2–$10 RPM initially; grows with watch-time and channel authority.
- **Podcasts:** $15–$30 CPM sponsorship after consistent downloads (>1k/listen).
- **Break-even:** Catalog of ~100 books typically covers setup costs via evergreen plays.

---

## 8. Technical Constraints

1. **CPU-only execution.** Keep pipeline accessible and low-cost (no GPU dependencies).
2. **Open-source stack.** Avoid paid APIs or licenses; maintain reproducibility.
3. **State fidelity.** `pipeline.json` is canonical; update only through orchestrator utilities.
4. **Logging & error handling.** Every phase must emit actionable messages and capture metrics.
5. **Modularity.** Do not couple phases; maintain per-phase configs/environment isolation.

---

## 9. Known Issues & Workarounds

| Issue | Description | Workaround |
|-------|-------------|------------|
| **Phase 4 lacks automated tests** | Production-proven, but no pytest coverage yet. | Rely on manual smoke test (`phase4_tts/test_simple_text.py --run`). Add coverage when bandwidth permits. |
| **Subtitle WER spikes on technical texts** | Whisper struggles with uncommon vocabulary. | Provide clean reference text via `--reference-text`; consider re-run with larger model. |
| **High RAM usage during large batches** | 10+ concurrent conversions can consume 24 GB+. | Lower worker count (`--workers 4`) or stagger manifest into smaller chunks. |
| **OCR inaccuracies on low-quality PDFs** | Scans with heavy artifacts reduce text yield. | Source alternate editions, or schedule manual text cleanup. |

---

## 10. Optimization Playbook

### 10.1 Speed
- Keep artifacts on NVMe storage.
- Disable antivirus scans for pipeline directories (Windows).
- Use manifest priorities to process high-impact titles first.
- Schedule overnight batches; monitor temps to avoid throttling.

### 10.2 Quality
- Maintain curated voice references suitable for each genre.
- Monitor Phase 4 validation logs for repeated failures; adjust chunk length or splitting thresholds.
- For poetry/drama, manually adjust chunk settings (shorter segments).
- If MOS proxy drops, inspect source text for formatting anomalies.

### 10.3 Revenue
- Craft YouTube titles with `"[Full Audiobook] Title — Subtitle"`.
- Add chapter timestamps via Phase 3 chunk metadata.
- Include end screens promoting related audiobooks.
- Translate descriptions into top viewer languages if analytics indicate demand.

---

## 11. Security & Backup

### 11.1 Critical Assets to Back Up
- `pipeline.json`
- `voice_assets/` (reference recordings)
- Finished audiobooks (`phase5_enhancement/processed/*.mp3`)
- Cover art templates / brand kit
- Documentation (this file, SOPs, manifests)

### 11.2 Suggested Strategy
| Frequency | Action |
|-----------|--------|
| Daily | Sync `pipeline.json` + manifests to cloud (via rclone/OneDrive). |
| Weekly | Copy completed audiobooks + subtitles to external SSD/NAS. |
| Monthly | Full repository snapshot (git bundle) + offsite backup. |

### 11.3 Access Control
- Repository remains private; limit access to trusted collaborators only.
- Use unique credentials for platform uploads (YouTube, podcast host).
- Maintain confidentiality agreements with contractors if sharing pipeline.

---

## 12. Documentation Index

| File | Purpose |
|------|---------|
| `PROJECT_OVERVIEW.md` | This document—business + technical blueprint. |
| `docs/Phase_2_3_Deep_Dive.md` | Advanced extraction and chunking notes. |
| `phase6_orchestrator/README.md` | Orchestrator usage & options. |
| `phase6_orchestrator/PIPELINE_JSON_SCHEMA.md` | Schema reference, validation rules. |
| `DEPENDENCY_CLEANUP_GUIDE.md` | Phased dependency pruning plan. |
| `scripts/README.md` | Utility scripts (backup, render_video). |

Keep documentation updated when processes evolve to ensure future continuity.

---

## 13. Future Enhancements

### 13.1 Phase 6.5 (In Design)
- Automated YouTube upload (YouTube Data API).
- Automated podcast RSS publishing.
- Cover art generator (template + optional AI backgrounds).
- Metadata templating & checklists.

### 13.2 Longer-Term Ideas
- Multi-language support (Spanish, French) using translation pipeline.
- Advanced narrator personalization (custom voices per genre).
- Audible/Findaway packaging automation (ACX specs).
- Patreon bundle generation (exclusive cuts, behind-the-scenes commentary).

---

## 14. Legal Compliance Checklist

1. **Public Domain Confirmation**
   - Published before 1928 (US) OR author deceased >70 years ago (check jurisdiction).
   - Document provenance (URL, screenshot, catalog entry).
   - Log verification in `docs/public_domain_registry.csv`.

2. **Reference Audio Legality**
   - Use LibriVox samples (public domain) or self-produced voice prompts.
   - Avoid cloning living narrators without consent.

3. **Platform Terms**
   - Adhere to YouTube monetization policies (e.g., re-used content avoidance).
   - Disclose AI-generated voice if platform requires.
   - Maintain records of source texts in case of disputes.

4. **Content Warnings**
   - Some classics include outdated or sensitive content; add disclaimers when appropriate.

---

## 15. Daily Operating Checklist

**Before Starting Batches**
- [ ] Verify new titles are public domain.
- [ ] Ensure `pipeline.json` backup exists.
- [ ] Confirm disk space ≥50 GB free.
- [ ] Update manifests with priority order.
- [ ] Check voice reference assignments.

**After Batch Completion**
- [ ] Review `pipeline.json` for any `status != "success"`.
- [ ] Spot-check audio and subtitles on 2–3 titles.
- [ ] Move finished masters to publishing queue.
- [ ] Update revenue tracking sheet with new releases.
- [ ] Back up deliverables.

**Weekly**
- [ ] Summarize analytics (YouTube, podcast). Identify winners.
- [ ] Clean old artifacts if not needed (archive first).
- [ ] Test restore from backup (random sample) to ensure continuity.

---

## 16. Business Continuity Plan

If primary operator is unavailable:
1. **Access**: Successor retrieves credentials (stored in password manager).
2. **Review**: Read `PROJECT_OVERVIEW.md`, `Orchestrator README`, and latest manifest.
3. **Current State**: Inspect `pipeline.json` to determine in-progress titles.
4. **Resume**: Use Phase 6/7 commands to continue batches.
5. **Publish**: Follow distribution SOP (located in `docs/publishing_checklist.md`).

Maintain updated contact list for:
- Voice talent collaborators (if any new voices introduced).
- Designers (cover art templates).
- Platform support channels (YouTube partner manager, podcast host).

---

## 17. Contact & Ownership

- **Primary Owner:** _[Your Name]_  
- **Technical Lead:** _[Same or designate]_  
- **Support:** Documented in password manager (support tickets, emails).

> **Reminder:** This pipeline is the core asset of the business. Protect the repository, keep documentation current, and treat runbooks as living documents.

---

**Current Focus:** Maintain stability, increase catalog volume, and refine monetization.  
**Next Milestone:** Automate publishing (Phase 6.5) to remove remaining manual steps.  
✅ All phases operational · 💰 Commercial-ready · 🧭 Private internal use only.
