import torch
from chatterbox.src.chatterbox.tts import ChatterboxTTS
model = ChatterboxTTS.from_pretrained(device='cpu')
wav = model.generate('Test sentence for TTS.', language_id='en')
import torchaudio
torchaudio.save('test.wav', wav, 24000)
print('Test WAV generated.')
