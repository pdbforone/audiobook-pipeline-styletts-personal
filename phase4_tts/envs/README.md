## Engine Environments

Phase 4 now keeps each engine inside its own Python virtual environment so heavy
dependencies stay isolated.

### Layout

```
phase4_tts/
  engine_runner.py           # ensures env + launches the engine
  envs/
    requirements_xtts.txt    # pinned deps for XTTS
    requirements_kokoro.txt  # deps for Kokoro
  .engine_envs/
    xtts/                    # auto-created virtualenv
    kokoro/                  # auto-created virtualenv
```

### Usage

The environments are created automatically the first time you run:

```bash
python engine_runner.py \
  --engine xtts \
  --file_id "MyBook" \
  --json_path ../pipeline.json \
  --disable_fallback
```

The runner looks for `python3.11` (recommended) to build the XTTS environment.
If you need a different interpreter, set `PHASE4_PYTHON_BIN` before calling the
runner.

To pre-create an environment manually:

```bash
python3.11 -m venv phase4_tts/.engine_envs/xtts
phase4_tts/.engine_envs/xtts/bin/pip install -r phase4_tts/envs/requirements_xtts.txt
```

Kokoro uses the same workflow but installs the lighter dependency set defined in
`requirements_kokoro.txt`.
