Kokoro huggingface readme ---
tags:
- audio
- text-to-speech
- onnx
base_model:
  - hexgrad/Kokoro-82M
inference: false
language: en
license: apache-2.0
library_name: txtai
---
# Kokoro Base (82M) Model for ONNX

[Kokoro 82M](https://huggingface.co/hexgrad/Kokoro-82M) export to ONNX. This model is the same ONNX file that's in the base repository. The voices file is from [this repository](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files).

## Usage with txtai

[txtai](https://github.com/neuml/txtai) has a built in Text to Speech (TTS) pipeline that makes using this model easy.

_Note: This requires txtai >= 8.3.0. Install from GitHub until that release._

```python
import soundfile as sf
from txtai.pipeline import TextToSpeech
# Build pipeline
tts = TextToSpeech("NeuML/kokoro-base-onnx")
# Generate speech
speech, rate = tts("Say something here")
# Write to file
sf.write("out.wav", speech, rate)
```

## Usage with ONNX

This model can also be run directly with ONNX provided the input text is tokenized. Tokenization can be done with [ttstokenizer](https://github.com/neuml/ttstokenizer). `ttstokenizer` is a permissively licensed library with no external dependencies (such as espeak).

Note that the txtai pipeline has additional functionality such as batching large inputs together that would need to be duplicated with this method.

```python
import json
import numpy as np
import onnxruntime
import soundfile as sf
from ttstokenizer import IPATokenizer
# This example assumes the files have been downloaded locally
with open("kokoro-base-onnx/voices.json", "r", encoding="utf-8") as f:
    voices = json.load(f)
# Create model
model = onnxruntime.InferenceSession(
    "kokoro-base-onnx/model.onnx",
    providers=["CPUExecutionProvider"]
)
# Create tokenizer
tokenizer = IPATokenizer()
# Tokenize inputs
inputs = tokenizer("Say something here")
# Get speaker array
speaker = np.array(voices["af"], dtype=np.float32)
# Generate speech
outputs = model.run(None, {
    "tokens": [[0, *inputs, 0]],
    "style": speaker[len(inputs)],
    "speed": np.ones(1, dtype=np.float32) * 1.0
})
# Write to file
sf.write("out.wav", outputs[0], 24000)
```

## Speaker reference

The Kokoro model has a number of built-in speakers.

When using this model, set a `speaker` id from the reference table below.

| SPEAKER     | GENDER   | NATIONALITY    | EXAMPLE                                                                                                             |
|:------------|:---------|:---------------|:------------------------------------------------------------------------------------------------------------------- |
| af          | F        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/af.mp3"></audio>           |
| af_bella    | F        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/af_bella.mp3"></audio>     |
| af_nicole   | F        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/af_nicole.mp3"></audio>    |
| af_sarah    | F        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/af_sarah.mp3"></audio>     |
| af_sky      | F        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/af_sky.mp3"></audio>       |
| am_adam     | M        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/am_adam.mp3"></audio>      |
| af_michael  | M        | American       | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/am_michael.mp3"></audio>   |
| bf_emma     | F        | British        | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/bf_emma.mp3"></audio>      |
| bf_isabella | F        | British        | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/bf_isabella.mp3"></audio>  |
| bm_george   | M        | British        | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/bm_george.mp3"></audio>    |
| bm_lewis    | M        | British        | <audio controls src="https://huggingface.co/NeuML/kokoro-base-onnx/resolve/main/examples/bm_lewis.mp3"></audio>     |

The following shows an example on how to set a speaker id when using txtai

```python
speech, rate = tts("Say something here", speaker="af_sky")