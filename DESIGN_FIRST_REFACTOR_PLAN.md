# Design-First Refactor Plan

## Vision

Transform the Personal Audiobook Studio from a collection of scripts into a **crafted system** - one that breathes, adapts, and delights. This isn't about writing code; it's about making a dent in the universe.

## Current State Analysis

### What We Have
- 464 Python files, 139 markdown documents
- Core pipeline: Phases 1-7 plus meta-phases (A-Z, AA-AD)
- 228KB orchestrator.py (monolithic, needs decomposition)
- Mixed concerns: business logic intertwined with I/O, UI, and infrastructure

### Pain Points
1. **Fragmented configuration** - voices.json vs voice_references.json (now unified)
2. **Monolithic orchestrator** - too many responsibilities
3. **Implicit contracts** - phases communicate via pipeline.json with undocumented schemas
4. **Scattered intelligence** - learning/adaptation logic spread across files
5. **No clear boundaries** - hard to test, hard to extend

## Proposed Architecture: Five Layers

```
+----------------------------------------------------------+
|                      INTERFACE                            |
|  CLI  |  Gradio UI  |  API (future)  |  Webhooks         |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                     ORCHESTRATE                           |
|  Pipeline Coordinator  |  Job Queue  |  State Machine    |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                       OBSERVE                             |
|  Metrics  |  Logging  |  Tracing  |  Health Checks       |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                        LEARN                              |
|  Policy Engine  |  Quality Feedback  |  Adaptation       |
+----------------------------------------------------------+
                            |
+----------------------------------------------------------+
|                      TRANSFORM                            |
|  Phase 1: Ingest  |  Phase 2: Parse  |  Phase 3: Chunk   |
|  Phase 4: TTS     |  Phase 5: Merge  |  Phase 6: Export  |
+----------------------------------------------------------+
```

### Layer Details

#### 1. TRANSFORM (Core Pipeline)
**Purpose**: Pure data transformation, no side effects beyond file I/O

| Phase | Input | Output | Responsibility |
|-------|-------|--------|----------------|
| Phase 1 | Raw files (PDF, EPUB, etc.) | Cleaned text | Extraction, normalization |
| Phase 2 | Text | Structured content | Parsing, metadata extraction |
| Phase 3 | Structured content | Chunks | Smart chunking, voice selection |
| Phase 4 | Chunks | Audio files | TTS synthesis |
| Phase 5 | Audio files | Merged audio | Concatenation, transitions |
| Phase 6 | Merged audio | Final output | Export, packaging |

**Design Principles**:
- Each phase is a pure function: `(input, config) -> (output, metrics)`
- No knowledge of other phases
- Idempotent: same input always produces same output
- Resumable: can restart from any checkpoint

#### 2. LEARN (Intelligence Layer)
**Purpose**: Adaptive behavior based on history and feedback

Components:
- **Policy Engine**: Dynamic decision-making (engine selection, quality thresholds)
- **Quality Feedback Loop**: Learn from synthesis results to improve future runs
- **Adaptation Rules**: Genre-aware tuning, voice optimization

**Current Location**: Scattered in `phaseZ_learning/`, `phaseQ_quality/`, policy files
**Target**: Consolidated `src/learn/` module with clear interfaces

#### 3. OBSERVE (Observability Layer)
**Purpose**: Understand what's happening, when, and why

Components:
- **Structured Logging**: Consistent log format across all phases
- **Metrics Collection**: Duration, success rates, quality scores
- **Tracing**: Request ID propagation for debugging
- **Health Checks**: System readiness, resource availability

**Design**: Decorator-based instrumentation, zero coupling to business logic

#### 4. ORCHESTRATE (Coordination Layer)
**Purpose**: Manage workflow, state, and job execution

Components:
- **Pipeline Coordinator**: Sequence phases, handle dependencies
- **State Machine**: Track pipeline.json state transitions
- **Job Queue**: Parallel chunk processing, retry logic
- **Resource Manager**: GPU allocation, memory limits

**Current**: 228KB `orchestrator.py` monolith
**Target**: Decomposed into focused modules with clear contracts

#### 5. INTERFACE (User Interaction Layer)
**Purpose**: Multiple ways to interact with the system

Components:
- **CLI**: Command-line interface for power users
- **Gradio UI**: Visual interface for interactive use
- **API**: RESTful endpoints for automation (future)
- **Webhooks**: Event notifications (future)

## Migration Strategy

### Phase 1: Foundation (Current)
- [x] Unify voice configuration
- [x] Add voice availability checking
- [ ] Document pipeline.json schema
- [ ] Add type hints to core modules

### Phase 2: Extract Concerns
- [ ] Extract logging into `src/observe/`
- [ ] Extract policy logic into `src/learn/`
- [ ] Create clear interfaces between layers

### Phase 3: Decompose Orchestrator
- [ ] Extract state machine logic
- [ ] Extract job queue logic
- [ ] Extract resource management
- [ ] Create `src/orchestrate/` module

### Phase 4: Harden Transform Layer
- [ ] Add input/output schemas for each phase
- [ ] Add comprehensive error handling
- [ ] Improve resumability

### Phase 5: Polish Interface Layer
- [ ] Unify CLI argument parsing
- [ ] Improve UI responsiveness
- [ ] Add progress reporting

## Success Criteria

1. **Testability**: Each layer can be tested in isolation
2. **Extensibility**: Adding a new phase requires < 100 lines of glue code
3. **Observability**: Any failure can be diagnosed from logs alone
4. **Performance**: No regression in processing speed
5. **Reliability**: Graceful degradation when components fail

## File Structure (Target)

```
audiobook-pipeline/
├── src/
│   ├── transform/          # Core pipeline phases
│   │   ├── phase1_ingest/
│   │   ├── phase2_parse/
│   │   ├── phase3_chunk/
│   │   ├── phase4_tts/
│   │   ├── phase5_merge/
│   │   └── phase6_export/
│   ├── learn/              # Intelligence layer
│   │   ├── policy_engine.py
│   │   ├── quality_feedback.py
│   │   └── adaptation.py
│   ├── observe/            # Observability
│   │   ├── logging.py
│   │   ├── metrics.py
│   │   └── tracing.py
│   ├── orchestrate/        # Coordination
│   │   ├── coordinator.py
│   │   ├── state_machine.py
│   │   └── job_queue.py
│   └── interface/          # User interaction
│       ├── cli/
│       ├── ui/
│       └── api/
├── configs/                # Shared configuration
├── tests/                  # Test suite
└── docs/                   # Documentation
```

## Immediate Next Steps

1. **Document pipeline.json schema** - Create JSON Schema for validation
2. **Add type hints** - Start with voice_selection.py (done), expand outward
3. **Extract first concern** - Logging is the safest starting point
4. **Write integration tests** - Capture current behavior before refactoring

---

*"The details are not the details. They make the design." - Charles Eames*
