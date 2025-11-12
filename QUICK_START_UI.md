# 🎙️ Quick Start: Personal Audiobook Studio

Two ways to launch the UI:

## 🖱️ Option 1: Double-Click Launcher (Easiest!)

Just double-click one of these files:

- **`Launch_Audiobook_Studio.bat`** - Simple batch launcher
- **`Launch_Studio.ps1`** - PowerShell launcher (prettier output)

The UI will automatically:
1. ✅ Check Python is installed
2. ✅ Start the server at http://localhost:7860
3. ✅ Open your browser automatically

**Keep the window open** while using the studio. Close it to stop the server.

## 💻 Option 2: Manual Terminal Launch

If you prefer the terminal:

```powershell
cd ui
python app.py
```

Then open: http://localhost:7860

## 🎯 First Time Setup

If the launcher fails, ensure:

1. **Python 3.8+** is installed and in PATH
2. **Dependencies installed**:
   ```powershell
   pip install gradio pyyaml
   ```

## 🚀 Using the Studio

1. **Upload a book** (PDF, EPUB, TXT, MOBI)
2. **Choose a voice** from your library
3. **Select TTS engine** (F5-TTS recommended for quality)
4. **Pick mastering preset** (audiobook_intimate for philosophy)
5. **Click "Generate Audiobook"**
6. Wait for processing (3-30 minutes depending on book length)
7. **Listen** to your finished audiobook!

### 🎛️ Advanced Options

Click "⚙️ Advanced Options" to:
- **Enable/disable resume** from checkpoint
- **Adjust max retries** per phase
- **Generate subtitles** for video
- **Select specific phases** to run (skip phases you already completed)

## 📊 What to Expect

**Short story (5K words):**
- Phase 1-3: 30 seconds
- Phase 4 (TTS): 2-5 minutes
- Phase 5 (Enhancement): 3-5 minutes
- **Total: ~8-10 minutes**

**Novel (100K words):**
- Phase 1-3: 1-2 minutes
- Phase 4 (TTS): 30-60 minutes
- Phase 5 (Enhancement): 10-20 minutes
- **Total: ~45-80 minutes**

## 🎨 Tips for Best Results

1. **Use F5-TTS engine** for expressive, natural speech
2. **Match voice to content:**
   - Philosophy → george_mckayland (contemplative, measured)
   - Fiction → landon_elkind (versatile, engaging)
   - Podcast → Any voice works
3. **Choose mastering preset by genre:**
   - Intimate: Philosophy, contemplative works
   - Dynamic: Fiction, adventure
   - Podcast: Casual, conversational
4. **Enable resume** to recover from interruptions
5. **Check Phase 5 config** if processing is slow (see QUICK_WINS.md)

## 🐛 Troubleshooting

**UI won't start:**
- Check Python is installed: `python --version`
- Install Gradio: `pip install gradio`

**Phase 5 is slow (>30 min for short story):**
- Check `phase5_enhancement/src/phase5_enhancement/config.yaml`
- Ensure `enable_phrase_cleanup: false`
- Ensure `max_workers: 4` (or more)

**Import errors:**
- Run setup script: `.\setup_excellence.ps1 -QuickWinsOnly`
- Or install manually: `pip install gradio pyyaml`

**Port already in use:**
- Another server is using port 7860
- Stop other Gradio apps or change port in `ui/app.py` (line 604)

## 🎉 Enjoy!

You're now ready to create insanely great audiobooks!

Questions? Check the full docs:
- `README_EXCELLENCE.md` - Complete documentation
- `CRAFT_EXCELLENCE_VISION.md` - Technical deep-dive
- `QUICK_WINS.md` - 3 hours to 10x quality
- `STATE_OF_THE_ART.md` - Advanced features

Happy narrating! 🎙️✨
