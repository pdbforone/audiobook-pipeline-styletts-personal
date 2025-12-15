Kokoro readme

TTS with onnx runtime based on Kokoro-TTS

🚀 Version 1.0 models are out now! 🎉

 podcast.mp4 
Features
Supports multiple languages
Fast performance near real-time on macOS M1
Offer multiple voices
Lightweight: ~300MB (quantized: ~80MB)
Setup
pip install -U kokoro-onnx
Instructions
Install uv for isolated Python (Recommend).
pip install uv
Create new project folder (you name it)
Run in the project folder
uv init -p 3.12
uv add kokoro-onnx soundfile
Paste the contents of examples/save.py in hello.py
Download the files kokoro-v1.0.onnx, and voices-v1.0.bin and place them in the same directory.
Run
uv run hello.py
You can edit the text in hello.py

That's it! audio.wav should be created.

Examples
See examples

Voices
See the latest voices and languages in Kokoro-82M/VOICES.md

Note: It's recommend to use misaki g2p package from v1.0, see examples

Contribute
See CONTRIBUTE.md

License
kokoro-onnx: MIT
kokoro model: Apache 2.0