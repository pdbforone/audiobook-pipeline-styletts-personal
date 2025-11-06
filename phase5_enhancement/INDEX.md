# Phase 5 Enhancement - Documentation Index

**📚 Start here when resuming work on this project**

---

## 📖 Documentation Files

### **1. QUICK_REFERENCE.md** ⚡ Start Here!
**Purpose**: Fast lookup for common tasks and current status  
**Use when**: You need to quickly check status or run a specific command  
**Contains**:
- Known issues summary
- Tool usage commands
- Current project status
- Success checklist

[→ Read QUICK_REFERENCE.md](./QUICK_REFERENCE.md)

---

### **2. SESSION_SUMMARY_Nov2025.md** 📝 Deep Dive
**Purpose**: Complete context from November 2025 work session  
**Use when**: You need full background or are debugging issues  
**Contains**:
- Detailed problem statement
- All approaches tried (what worked/didn't work)
- File locations and purpose
- Key learnings
- Future improvement recommendations

[→ Read SESSION_SUMMARY_Nov2025.md](./SESSION_SUMMARY_Nov2025.md)

---

### **3. This File (INDEX.md)** 🗂️
**Purpose**: Navigation hub for Phase 5 documentation  
**Use when**: You're lost or need to find the right document

---

## 🎯 Quick Decision Tree

**Choose your starting point:**

```
┌─ Need to work on Meditations audiobook?
│  └─→ Read QUICK_REFERENCE.md
│     └─→ Check "Current State" section
│        └─→ Follow "Recommended Workflow"
│
┌─ Debugging Phase 5 issues?
│  └─→ Read SESSION_SUMMARY_Nov2025.md
│     └─→ See "What We Tried" section
│        └─→ Check "Known Issues"
│
┌─ Starting a new audiobook project?
│  └─→ Read SESSION_SUMMARY_Nov2025.md
│     └─→ See "Key Learnings" section
│        └─→ Apply lessons to avoid same issues
│
└─ Continuing after a break?
   └─→ Read QUICK_REFERENCE.md first
      └─→ Check validation_report.txt for latest metrics
         └─→ Read relevant sections of SESSION_SUMMARY
```

---

## 🛠️ Tools Created This Session

All located in: `phase5_enhancement/`

| Tool | Purpose | Status |
|------|---------|--------|
| `validate_subtitles.py` | Compare subtitles vs source text | ✅ Working |
| `extract_phrase_timestamps.py` | Generate Audacity timestamp list | ✅ Recommended |
| `surgical_phrase_remover.py` | Word-level phrase removal | ⚠️ Slow/Untested |
| `diagnose_whisper.py` | Debug Whisper transcription | ✅ Diagnostic only |

---

## 📊 Current Project Files

**Audio**:
- `processed/meditations_audiobook.mp3` - Current version (has 99 phrases)
- `meditations_chunks/` - 899 source chunks from Phase 4

**Subtitles**:
- `processed/meditations_audiobook.srt` - Current (5,513 segments)

**Validation**:
- `validation_report.txt` - Latest metrics (81% accuracy)

**Source**:
- `phase2-extraction/extracted_text/the meditations, by Marcus Aurelius.txt` - Original text (44,743 words)

---

## 🚀 Most Common Tasks

### **1. Validate Current Subtitles**
```bash
poetry run python validate_subtitles.py \
  --phase2-text "C:\Users\myson\Pipeline\audiobook-pipeline-chatterbox\phase2-extraction\extracted_text\the meditations, by Marcus Aurelius.txt" \
  --subtitle-file "processed\meditations_audiobook.srt"
```

### **2. Extract Timestamps for Audacity**
```bash
poetry run python extract_phrase_timestamps.py
```

### **3. Generate New Subtitles**
```bash
poetry run python generate_subtitles.py --input processed/meditations_audiobook.mp3
```

---

## ⚠️ Critical Notes

1. **Phase 5 phrase cleaning is broken** - Only processes 36/899 files
2. **Use Audacity workaround** - Manual removal is most reliable
3. **Always validate** - Run validation before YouTube upload
4. **81% accuracy is too low** - Should be >98% before shipping

---

## 📅 Version History

- **November 3, 2025**: Initial documentation created
  - Identified Phase 5 issues
  - Created validation and timestamp tools
  - Documented workaround approach

---

## 🔄 Handoff Checklist

**When resuming this project:**
- [ ] Read QUICK_REFERENCE.md "Current State"
- [ ] Check `validation_report.txt` date
- [ ] Look for `meditations_audiobook_FINAL.mp3`
- [ ] If FINAL exists, validate it
- [ ] If not, follow Audacity workflow in QUICK_REFERENCE

**Before starting new audiobook:**
- [ ] Read "Key Learnings" in SESSION_SUMMARY
- [ ] Check if Phase 5 issues are fixed
- [ ] Use validation script from day 1
- [ ] Monitor accuracy throughout pipeline

---

**Questions? Check:**
1. QUICK_REFERENCE.md for how-to
2. SESSION_SUMMARY_Nov2025.md for why
3. validation_report.txt for current state

**Good luck! 🎧**
