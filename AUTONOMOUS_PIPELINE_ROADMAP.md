# Autonomous Pipeline Roadmap
## From Scripted Pipeline → Intelligent Audiobook Engine

> *"The people who are crazy enough to think they can change the world are the ones who do."*

---

## Executive Summary

This document outlines the evolution of the Personal Audiobook Studio from a **deterministic pipeline** to an **autonomous, self-healing system** with local AI reasoning capabilities.

**Key Principle:** Local-first, CPU-friendly, no external API dependencies.

---

## Current State Analysis

### What Already Exists (Foundations to Build Upon)

| Component | Location | Capability |
|-----------|----------|------------|
| **EngineManager** | `phase4_tts/engines/engine_manager.py` | Multi-engine fallback, RTF-based switching, lazy loading |
| **TuningOverridesStore** | `policy_engine/policy_engine.py` | Self-tuning chunk sizes, engine preference learning, voice streak tracking |
| **PolicyEngine** | `pipeline_common/policy_engine.py` | Decision hooks, learning modes (observe/enforce/tune) |
| **State Manager** | `pipeline_common/state_manager.py` | Atomic transactions, cross-platform locking, backup rotation |
| **RTF Monitoring** | `phase4_tts/` | Real-time factor tracking, latency fallback |

### Hardware Constraints

```
CPU:     AMD Ryzen 5 5500U (6c/12t @ 2.1 GHz)
RAM:     16 GB (~12 GB usable for ML)
GPU:     None (integrated Radeon, not for inference)
Storage: 466 GB SSD
OS:      Windows 11 x64
```

**Implication:** All new components must be CPU-friendly. LLM inference must use quantized models.

---

## Gap Analysis

### What's Proposed vs. What Exists

| Proposed Feature | Current State | Gap |
|------------------|---------------|-----|
| Local Llama integration | None | **NEW** - Need llama.cpp/Ollama layer |
| Multi-engine TTS (6+ engines) | 2 engines (XTTS, Kokoro) | **PARTIAL** - Add Piper, evaluate others |
| Self-repair agent | PolicyAdvisor exists | **EXTEND** - Add log parsing + patch suggestion |
| Adaptive chunking via LLM | Heuristic-based (Phase 3) | **ENHANCE** - Add semantic LLM layer |
| Metadata generation | None | **NEW** - Add local AI metadata suite |
| Benchmarking suite | RTF metrics only | **EXTEND** - Add comprehensive profiling |
| Dead-chunk repair | Fallback to different engine | **ENHANCE** - Add chunk splitting + rewrite |

---

## Phased Implementation Plan

### Phase A: Foundation Hardening (Priority: Critical)
*Estimated effort: 1-2 weeks*

**Goal:** Fix known gaps before adding complexity.

#### A.1: Phase 4 Chunk Granularity Fix
The current 250-character limit is a surface symptom. Real fix:

```python
# Current: Hardcoded limit
MAX_CHARS = 250  # Wrong

# Target: Engine-aware tokenizer limits
class EngineCapability:
    max_tokens: int          # e.g., 400 for XTTS, 512 for Kokoro
    chars_per_token: float   # ~4.0 for English

    @property
    def max_chars(self) -> int:
        return int(self.max_tokens * self.chars_per_token * 0.9)  # 10% safety margin
```

**Changes:**
- [ ] Add `engine_capabilities.yaml` registry with per-engine limits
- [ ] Compute token-based thresholds dynamically
- [ ] Phase 4 writes granular chunk data:

```json
{
  "chunk_0001": {
    "status": "success",
    "engine_used": "xtts",
    "text_length": 847,
    "token_count": 212,
    "audio_path": "...",
    "duration_seconds": 12.4,
    "rt_factor": 1.8,
    "validation": {
      "tier1_passed": true,
      "tier2_wer": 0.05
    }
  }
}
```

#### A.2: Orchestrator Success Detection Fix
```python
# Current (fragile):
success = returncode == 0

# Target (robust):
success = (
    returncode == 0
    and len(chunk_audio_paths) == total_chunks
    and all(Path(p).exists() for p in chunk_audio_paths)
)
```

---

### Phase B: Engine Ecosystem Expansion (Priority: High)
*Estimated effort: 2-3 weeks*

**Goal:** Add CPU-friendly engines with automatic capability detection.

#### B.1: Engine Registry
Create `phase4_tts/engine_registry.yaml`:

```yaml
engines:
  xtts:
    class: phase4_tts.engines.xtts_engine.XTTSEngine
    cpu_friendly: true
    max_tokens: 400
    sample_rate: 24000
    languages: [en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko]
    supports_cloning: true
    typical_rtf_cpu: 3.2
    memory_mb: 4000

  kokoro:
    class: phase4_tts.engines.kokoro_engine.KokoroEngine
    cpu_friendly: true
    max_tokens: 512
    sample_rate: 24000
    languages: [en]
    supports_cloning: false
    typical_rtf_cpu: 1.3
    memory_mb: 800

  piper:  # NEW
    class: phase4_tts.engines.piper_engine.PiperEngine
    cpu_friendly: true
    max_tokens: 1000
    sample_rate: 22050
    languages: [en, de, es, fr, it, pl, pt, ru, uk, nl]
    supports_cloning: false
    typical_rtf_cpu: 0.3  # Very fast
    memory_mb: 200
    voices:
      - en_US-lessac-medium
      - en_US-amy-medium
      - en_GB-alan-medium
```

#### B.2: Add Piper Engine (CPU-Friendly, Fast)
**Why Piper first:**
- Apache-2.0 license
- RTF ~0.3 on CPU (10x faster than XTTS)
- Small models (~50-200MB)
- Good quality voices available
- Perfect for draft/proofing mode

```python
# phase4_tts/engines/piper_engine.py
class PiperEngine(TTSEngine):
    name = "Piper (Ultra-Fast CPU)"
    supports_emotions = False
    sample_rate = 22050

    def __init__(self, device: str = "cpu", voice: str = "en_US-lessac-medium"):
        self.voice = voice
        # Uses piper-tts package
```

#### B.3: Engine Capability Profiling
Runtime profiling that updates registry:

```python
class EngineProfiler:
    def profile_engine(self, engine_name: str) -> EngineProfile:
        """Run benchmark and return capabilities"""
        return EngineProfile(
            max_chars=self._find_max_chars(engine),
            typical_rtf=self._measure_rtf(engine, test_texts),
            memory_mb=self._measure_memory(engine),
            failure_patterns=self._detect_failure_patterns(engine),
            stability_score=self._compute_stability(results)
        )
```

---

### Phase C: Local Llama Intelligence Layer (Priority: High)
*Estimated effort: 3-4 weeks*

**Goal:** Add local LLM reasoning without external dependencies.

#### C.1: Llama Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLAMA INTELLIGENCE LAYER                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐│
│  │   Chunk     │  │  Pipeline   │  │   Chunk     │  │Metadata ││
│  │ Intelligence│  │  Reasoner   │  │  Rewriter   │  │Generator││
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘│
│         │                │                │              │      │
│         └────────────────┴────────────────┴──────────────┘      │
│                              │                                  │
│                    ┌─────────▼─────────┐                        │
│                    │   Ollama Server   │                        │
│                    │  (llama.cpp/GGUF) │                        │
│                    └───────────────────┘                        │
│                              │                                  │
│                    ┌─────────▼─────────┐                        │
│                    │  Quantized Model  │                        │
│                    │  (Q4_K_M, ~4GB)   │                        │
│                    └───────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

#### C.2: Model Selection for CPU Constraints

| Model | Size | RAM Required | Speed (tok/s) | Use Case |
|-------|------|--------------|---------------|----------|
| **Phi-3-mini-4k (Q4_K_M)** | 2.4 GB | ~4 GB | ~15 tok/s | Fast reasoning, short context |
| **Llama-3.2-3B (Q4_K_M)** | 2.0 GB | ~3.5 GB | ~18 tok/s | Balanced quality/speed |
| **Mistral-7B (Q4_K_M)** | 4.1 GB | ~6 GB | ~8 tok/s | Best quality, slower |
| **TinyLlama-1.1B (Q8_0)** | 1.1 GB | ~2 GB | ~30 tok/s | Ultra-fast, simpler tasks |

**Recommendation:** Start with **Phi-3-mini** or **Llama-3.2-3B** for best quality/speed balance.

#### C.3: Agent Implementations

```python
# agents/llama_base.py
class LlamaAgent:
    def __init__(self, model: str = "phi3:mini"):
        self.client = ollama.Client()
        self.model = model

    def query(self, prompt: str, max_tokens: int = 500) -> str:
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={"num_predict": max_tokens}
        )
        return response["response"]
```

**Agent: Chunk Intelligence** (`agents/llama_chunker.py`)
```python
class LlamaChunker(LlamaAgent):
    """Semantic chunk boundary detection using LLM reasoning"""

    SYSTEM_PROMPT = """You are a text segmentation expert for audiobook production.
    Given text, identify optimal break points that:
    1. Preserve semantic coherence
    2. Respect natural speech pauses
    3. Keep chunks between 600-1000 characters
    4. Never break mid-sentence

    Output JSON: {"boundaries": [char_positions], "reasoning": "..."}"""

    def find_boundaries(self, text: str) -> List[int]:
        response = self.query(f"{self.SYSTEM_PROMPT}\n\nText:\n{text[:4000]}")
        return self._parse_boundaries(response)
```

**Agent: Pipeline Reasoner** (`agents/llama_reasoner.py`)
```python
class LlamaReasoner(LlamaAgent):
    """Analyzes pipeline failures and suggests fixes"""

    def analyze_failure(self, log_content: str, chunk_data: dict) -> PatchSuggestion:
        prompt = f"""Analyze this TTS pipeline failure:

Log:
{log_content[-2000:]}

Chunk data:
{json.dumps(chunk_data, indent=2)}

Identify:
1. Root cause
2. Suggested fix (code or config change)
3. Prevention strategy

Output as JSON."""

        response = self.query(prompt)
        return self._parse_suggestion(response)
```

**Agent: Chunk Rewriter** (`agents/llama_rewriter.py`)
```python
class LlamaRewriter(LlamaAgent):
    """Rewrites problematic chunks for TTS compatibility"""

    def rewrite_for_tts(self, text: str, max_chars: int, issues: List[str]) -> str:
        prompt = f"""Rewrite this text for TTS synthesis.

Original ({len(text)} chars, max {max_chars}):
{text}

Issues detected: {issues}

Requirements:
1. Stay under {max_chars} characters
2. Preserve ALL meaning (no hallucinations)
3. Fix pronunciation issues
4. Break into smaller semantic units if needed

Output the rewritten text only."""

        return self.query(prompt, max_tokens=max_chars // 3)
```

**Agent: Metadata Generator** (`agents/llama_metadata.py`)
```python
class LlamaMetadataGenerator(LlamaAgent):
    """Generates audiobook metadata using local LLM"""

    def generate_chapter_summary(self, chapter_text: str) -> str:
        # Short summary for chapter description

    def generate_youtube_metadata(self, book_info: dict) -> dict:
        # Title, description, tags for YouTube SEO

    def generate_timestamps(self, chunks: List[dict]) -> List[dict]:
        # Chapter timestamps for video description
```

#### C.4: Resource Management

```python
class LlamaResourceManager:
    """Manages Ollama lifecycle to avoid memory conflicts with TTS"""

    def __init__(self, max_memory_mb: int = 5000):
        self.max_memory = max_memory_mb
        self.active = False

    def acquire(self) -> bool:
        """Start Ollama if memory available"""
        available = psutil.virtual_memory().available // (1024 * 1024)
        if available < self.max_memory:
            logger.warning(f"Insufficient RAM for LLM: {available}MB < {self.max_memory}MB")
            return False
        self._start_ollama()
        self.active = True
        return True

    def release(self):
        """Stop Ollama to free memory for TTS"""
        if self.active:
            self._stop_ollama()
            self.active = False
```

---

### Phase D: Self-Repair & Resilience (Priority: Medium)
*Estimated effort: 2 weeks*

**Goal:** Pipeline that diagnoses and suggests fixes for its own failures.

#### D.1: Self-Healing Agent Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    SELF-HEALING LOOP                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐     ┌──────────┐     ┌────────────┐           │
│   │ Failure │────►│   Log    │────►│   Llama    │           │
│   │ Detect  │     │  Parser  │     │  Reasoner  │           │
│   └─────────┘     └──────────┘     └────────────┘           │
│                                           │                  │
│                                           ▼                  │
│   ┌─────────┐     ┌──────────┐     ┌────────────┐           │
│   │  User   │◄────│  Staging │◄────│   Patch    │           │
│   │ Approval│     │   Queue  │     │ Generator  │           │
│   └─────────┘     └──────────┘     └────────────┘           │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────┐                                               │
│   │  Apply  │  (Only after human approval)                  │
│   │  Patch  │                                               │
│   └─────────┘                                               │
└──────────────────────────────────────────────────────────────┘
```

#### D.2: Log Parser

```python
class PipelineLogParser:
    """Extracts structured failure information from logs"""

    PATTERNS = {
        "oom": r"(out of memory|MemoryError|CUDA OOM)",
        "timeout": r"(timeout|timed out|exceeded \d+ seconds)",
        "truncation": r"(truncat|text too long|max.*exceeded)",
        "audio_quality": r"(silence detected|no audio|corrupt|invalid wav)",
        "pydantic": r"(ValidationError|pydantic)",
    }

    def parse(self, log_path: Path) -> List[FailureEvent]:
        events = []
        for line in self._tail_log(log_path, lines=500):
            for category, pattern in self.PATTERNS.items():
                if re.search(pattern, line, re.I):
                    events.append(FailureEvent(
                        category=category,
                        line=line,
                        timestamp=self._extract_timestamp(line)
                    ))
        return events
```

#### D.3: Patch Staging (Never Auto-Apply)

```python
class PatchStaging:
    """Stages suggested patches for human review"""

    STAGING_DIR = Path(".pipeline/staged_patches")

    def stage_patch(self, suggestion: PatchSuggestion) -> Path:
        patch_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_file = self.STAGING_DIR / f"{patch_id}_{suggestion.target}.patch"

        patch_file.write_text(json.dumps({
            "id": patch_id,
            "target": suggestion.target,
            "description": suggestion.description,
            "diff": suggestion.diff,
            "confidence": suggestion.confidence,
            "reasoning": suggestion.reasoning,
            "created_at": datetime.now().isoformat(),
            "status": "pending_review"  # Never auto-applied
        }, indent=2))

        logger.info(f"Patch staged for review: {patch_file}")
        return patch_file
```

#### D.4: Dead-Chunk Repair Mode

```python
class DeadChunkRepair:
    """Attempts to recover failed chunks through multiple strategies"""

    def repair(self, chunk: FailedChunk) -> Optional[AudioResult]:
        strategies = [
            self._try_smaller_splits,
            self._try_different_engine,
            self._try_text_rewrite,
            self._try_simplified_text,
        ]

        for strategy in strategies:
            try:
                result = strategy(chunk)
                if result and result.is_valid():
                    self._log_success(chunk, strategy.__name__)
                    return result
            except Exception as e:
                self._log_attempt(chunk, strategy.__name__, e)
                continue

        # All strategies failed
        self._add_to_error_registry(chunk)
        return None

    def _try_smaller_splits(self, chunk: FailedChunk) -> Optional[AudioResult]:
        """Split into 2-4 smaller chunks and concatenate"""
        sub_chunks = self.chunker.split_further(
            chunk.text,
            max_size=chunk.text_length // 3
        )
        audios = [self.engine.synthesize(sc) for sc in sub_chunks]
        return self.concatenator.join(audios)
```

---

### Phase E: Benchmarking & Adaptive Tuning (Priority: Medium)
*Estimated effort: 1-2 weeks*

**Goal:** Data-driven optimization of chunk sizes, engine selection, and resource usage.

#### E.1: Comprehensive Benchmark Suite

```python
class PipelineBenchmark:
    """Full system performance profiling"""

    def run_benchmark(self) -> BenchmarkReport:
        return BenchmarkReport(
            cpu=self._benchmark_cpu(),
            memory=self._benchmark_memory(),
            disk=self._benchmark_disk(),
            engines=self._benchmark_all_engines(),
            chunking=self._benchmark_chunking(),
            recommendations=self._generate_recommendations()
        )

    def _benchmark_all_engines(self) -> Dict[str, EngineMetrics]:
        test_texts = self._load_test_corpus()  # Various lengths, genres
        results = {}

        for engine_name in self.engine_manager.engines:
            metrics = []
            for text in test_texts:
                start = time.time()
                audio = self.engine_manager.synthesize(text, engine=engine_name)
                elapsed = time.time() - start

                metrics.append(EngineMetrics(
                    text_length=len(text),
                    audio_duration=len(audio) / 24000,
                    wall_time=elapsed,
                    rtf=elapsed / (len(audio) / 24000),
                    memory_peak=self._get_memory_peak()
                ))

            results[engine_name] = self._aggregate_metrics(metrics)

        return results
```

#### E.2: Adaptive Chunk Size Learning

```python
class AdaptiveChunker:
    """Learns optimal chunk sizes from runtime performance"""

    def __init__(self):
        self.history = ChunkPerformanceHistory()

    def get_optimal_size(self, genre: str, engine: str) -> ChunkSizeConfig:
        # Query historical performance
        stats = self.history.query(genre=genre, engine=engine)

        if stats.sample_count < 50:
            # Not enough data, use defaults
            return self.defaults[genre]

        # Find size that minimizes failures while maximizing throughput
        optimal = self._optimize(
            stats.size_vs_failure_rate,
            stats.size_vs_rtf,
            weights={"failure": 0.7, "speed": 0.3}
        )

        return ChunkSizeConfig(
            min_chars=optimal.min_safe,
            soft_max=optimal.sweet_spot,
            hard_max=optimal.absolute_max,
            source="adaptive_learning"
        )
```

---

### Phase F: Metadata Suite (Priority: Low)
*Estimated effort: 1 week*

**Goal:** Local-only AI-generated metadata for audiobook publishing.

#### F.1: Metadata Generation Pipeline

```python
class MetadataGenerator:
    """Generate publishing-ready metadata using local LLM"""

    def generate_full_metadata(self, book: ProcessedBook) -> BookMetadata:
        return BookMetadata(
            title=book.title,
            author=book.author,

            # LLM-generated
            short_description=self.llm.summarize(book.full_text, max_words=50),
            long_description=self.llm.summarize(book.full_text, max_words=300),

            chapters=[
                ChapterMeta(
                    title=ch.detected_title or self.llm.generate_title(ch.text),
                    timestamp=ch.start_time,
                    summary=self.llm.summarize(ch.text, max_words=30)
                )
                for ch in book.chapters
            ],

            # SEO
            youtube_title=self._format_youtube_title(book),
            youtube_description=self._generate_youtube_description(book),
            youtube_tags=self.llm.extract_tags(book.full_text),

            # Accessibility
            ell_summary=self.llm.simplify_for_ell(book.full_text[:2000])
        )
```

---

## Directory Structure Evolution

```
audiobook-pipeline/
├── agents/                          # NEW: AI agent layer
│   ├── __init__.py
│   ├── llama_base.py               # Base Ollama client
│   ├── llama_chunker.py            # Semantic chunking
│   ├── llama_reasoner.py           # Failure analysis
│   ├── llama_rewriter.py           # Text repair
│   ├── llama_metadata.py           # Metadata generation
│   └── resource_manager.py         # Memory management
│
├── core/                            # NEW: Shared core logic
│   ├── __init__.py
│   ├── engine_registry.py          # Engine capabilities
│   ├── benchmark.py                # Performance profiling
│   ├── adaptive_chunker.py         # Learning-based chunking
│   └── repair_strategies.py        # Dead-chunk recovery
│
├── self_repair/                     # NEW: Self-healing layer
│   ├── __init__.py
│   ├── log_parser.py               # Failure extraction
│   ├── patch_generator.py          # Suggest fixes
│   ├── patch_staging.py            # Safe staging queue
│   └── repair_loop.py              # Main repair orchestration
│
├── phase4_tts/
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── engine_manager.py       # EXISTING: Enhanced
│   │   ├── xtts_engine.py          # EXISTING
│   │   ├── kokoro_engine.py        # EXISTING
│   │   └── piper_engine.py         # NEW: Ultra-fast CPU
│   ├── engine_registry.yaml        # NEW: Capabilities
│   └── ...
│
├── policy_engine/
│   ├── policy_engine.py            # EXISTING: Extended
│   ├── advisor.py                  # EXISTING: Extended
│   └── learning_loop.py            # NEW: Continuous tuning
│
├── models/
│   ├── registry.json               # Engine + LLM capabilities
│   └── benchmark_results.json      # Performance data
│
└── .pipeline/
    ├── staged_patches/             # NEW: Pending fixes
    ├── benchmark_history/          # NEW: Performance logs
    └── llm_cache/                  # NEW: Response cache
```

---

## Implementation Priority Matrix

| Phase | Component | Priority | Dependencies | Risk |
|-------|-----------|----------|--------------|------|
| **A** | Phase 4 chunk granularity | Critical | None | Low |
| **A** | Orchestrator success fix | Critical | None | Low |
| **B** | Engine registry | High | Phase A | Low |
| **B** | Piper engine | High | Engine registry | Low |
| **B** | Engine profiling | High | Piper engine | Medium |
| **C** | Ollama integration | High | None | Medium |
| **C** | Llama chunker | High | Ollama | Medium |
| **C** | Llama reasoner | Medium | Ollama | Medium |
| **C** | Resource manager | High | Ollama | Low |
| **D** | Log parser | Medium | None | Low |
| **D** | Patch staging | Medium | Log parser | Low |
| **D** | Dead-chunk repair | Medium | Llama rewriter | Medium |
| **E** | Benchmark suite | Medium | Engine registry | Low |
| **E** | Adaptive chunker | Medium | Benchmark suite | Medium |
| **F** | Metadata generator | Low | Llama base | Low |

---

## Risk Mitigation

### RAM Contention (LLM vs TTS)
**Risk:** Running Llama and XTTS simultaneously may exceed 12GB usable RAM.

**Mitigation:**
1. Never run LLM inference during TTS synthesis
2. Use ResourceManager to orchestrate loading/unloading
3. Prefer smaller models (Phi-3-mini over Mistral-7B)
4. Cache LLM responses aggressively

### Model Quality Variance
**Risk:** Quantized models may produce lower-quality reasoning.

**Mitigation:**
1. Use Q4_K_M or Q5_K_M quantization (best quality/size balance)
2. Implement confidence scoring for LLM outputs
3. Fall back to heuristics when LLM confidence < 0.7
4. A/B test LLM decisions vs heuristic baselines

### Backward Compatibility
**Risk:** New components may break existing pipelines.

**Mitigation:**
1. All new features are opt-in via config flags
2. Existing pipeline.json schema remains unchanged
3. New fields use `_v2` suffix or nested objects
4. Comprehensive migration tests

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Chunk failure rate | ~5% | <1% | `failed_chunks / total_chunks` |
| Mean RTF (XTTS) | 3.2 | 2.8 | Wall time / audio duration |
| Self-repair success | N/A | >60% | Repaired chunks / failed chunks |
| Pipeline autonomy | Manual | Semi-auto | Human interventions per book |
| Metadata quality | None | Usable | Human review score (1-5) |

---

## Next Steps

1. **Immediate:** Implement Phase A fixes (chunk granularity, orchestrator success)
2. **This week:** Set up engine registry, add Piper engine
3. **Next week:** Install Ollama, implement llama_base.py
4. **Following weeks:** Implement agents one by one, testing each

---

## Appendix: Engine Evaluation Matrix

| Engine | CPU RTF | Quality | Cloning | License | Verdict |
|--------|---------|---------|---------|---------|---------|
| XTTS v2 | 3.2 | Excellent | Yes | Coqui (NC) | **Primary** |
| Kokoro | 1.3 | Good | No | Apache-2.0 | **Fast fallback** |
| Piper | 0.3 | Good | No | Apache-2.0 | **Ultra-fast draft** |
| Bark | 8.0+ | Variable | No | MIT | Not recommended (too slow) |
| FishSpeech | GPU-only | Excellent | Yes | Apache-2.0 | Future (needs GPU) |
| LlamaTTS | Unknown | Experimental | Unknown | Unknown | Evaluate later |

---

*This roadmap transforms the pipeline from a script executor into an intelligent, self-improving system—while respecting the CPU-only, local-first philosophy that makes it accessible to everyone.*
