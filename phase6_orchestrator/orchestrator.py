#!/usr/bin/env python3
"""
Phase 6: Single-File Orchestrator (Enhanced)
Production-ready orchestrator - runs phases 1-5 sequentially with:
- Rich progress reporting
- Robust Conda environment handling
- Resume from checkpoints
- Error handling with retries
- Actionable error messages
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import yaml
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Resolve project roots for cross-phase imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PHASE1_SRC = PROJECT_ROOT / "phase1-validation" / "src"

for _path in (PROJECT_ROOT, PHASE1_SRC):
    if _path.exists() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

# Add parent directory to path for pipeline_common
from pipeline_common import PipelineState, StateError, ensure_phase_and_file
from pipeline_common.policy_engine import PolicyEngine
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from autonomy.profiles import export_profiles, reset_profiles
from autonomy.trace_recorder import begin_run_trace, finalize_trace, record_event
from autonomy.feature_attribution import explain_recommendations
from autonomy import introspection as auto_introspection
from long_horizon import aggregator as lh_aggregator
from long_horizon import patterns as lh_patterns
from long_horizon import forecaster as lh_forecaster
from autonomy import long_horizon as auto_long_horizon
from autonomy import trends as auto_trends
from autonomy import predictive as auto_predictive
from autonomy.stability_bounds import check_stability_bounds
from autonomy.drift_detection import detect_drift
from autonomy.safety_envelope import apply_safety_envelope
from autonomy.safety_escalation import evaluate_escalation, apply_escalation, load_safety_state, write_safety_state
from autonomy.safety_log import log_safety_event
from phaseAA.global_safety_envelope import enforce_global_safety
from introspection.cluster import cluster_anomalies
from introspection.narratives import generate_narrative
from introspection.critic import self_critique
from introspection.summary import build_introspection_summary

# Lazy import for LlamaReasoner to avoid import errors if agents not available
_LLAMA_REASONER = None
_LLAMA_DIRECTOR = None
_LAST_PHASE_ERROR = ""  # Stores last error output for AI analysis

# Lazy import for ErrorRegistry (self-repair tracking)
_ERROR_REGISTRY = None
_DEAD_CHUNK_REPAIR = None

# Experiment state (reset after each run to avoid leakage)
_ACTIVE_EXPERIMENT = None
_TEMP_EXPERIMENT_OVERRIDES: Dict[str, Any] = {}
_EXPERIMENT_CONTEXT: Dict[str, Any] = {}
_CURRENT_EXPERIMENT = None
_SUPERVISED_OVERRIDES: Dict[str, Any] = {}
_AUTONOMOUS_OVERRIDES: Dict[str, Any] = {}
_RUN_TRACE: Optional[Dict[str, Any]] = None


def get_book_dir(file_id: str) -> Path:
    """Gets the dedicated directory for a book's metadata."""
    return PROJECT_ROOT / ".pipeline" / "books" / file_id

def _get_audiobook_director(book_text: str):
    """Lazy-load AudiobookDirector."""
    global _LLAMA_DIRECTOR
    if _LLAMA_DIRECTOR is None:
        try:
            from agents.audiobook_director import AudiobookDirector
            _LLAMA_DIRECTOR = AudiobookDirector(book_text=book_text)
            logger.debug("AudiobookDirector loaded successfully")
        except ImportError:
            logger.debug("AudiobookDirector not available (agents module not found)")
            _LLAMA_DIRECTOR = False
        except Exception as e:
            logger.debug(f"AudiobookDirector init failed: {e}")
            _LLAMA_DIRECTOR = False
    return _LLAMA_DIRECTOR if _LLAMA_DIRECTOR else None


def run_phase_0_director(file_id: str, file_path: Path, pipeline_json: Path) -> bool:
    """
    Runs the AudiobookDirector agent to create the Production Bible for a book.
    """
    book_dir = get_book_dir(file_id)
    bible_path = book_dir / "production_bible.json"

    if bible_path.exists():
        logger.info(f"Production Bible already exists at {bible_path}. Skipping generation.")
        return True

    try:
        with file_path.open("r", encoding="utf-8") as f:
            book_text = f.read()
    except Exception as e:
        logger.error(f"Phase 0 Error: Could not read book text from {file_path}. {e}")
        return False

    director = _get_audiobook_director(book_text)
    if not director:
        logger.error("Phase 0 Error: Could not load the AudiobookDirector agent.")
        return False
    
    try:
        production_bible = director.create_production_bible()
        if not production_bible:
            logger.error("Phase 0 Error: AudiobookDirector failed to create a production bible.")
            return False

        book_dir.mkdir(parents=True, exist_ok=True)
        with bible_path.open("w", encoding="utf-8") as f:
            json.dump(production_bible, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Production Bible successfully created at {bible_path}")
        return True

    except Exception as e:
        logger.error(f"Phase 0 Error: An exception occurred during production bible creation: {e}", exc_info=True)
        return False


def _write_json_safely(path: Path, payload: Dict[str, Any]) -> None:
    """Write JSON to disk without affecting runtime on failure."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Failed to write profile output to %s", path)


def _get_error_registry() -> Optional[Any]:
    """Lazy-load ErrorRegistry for tracking chunk failures."""
    global _ERROR_REGISTRY
    if _ERROR_REGISTRY is None:
        try:
            from self_repair.repair_loop import ErrorRegistry
            _ERROR_REGISTRY = ErrorRegistry()
            logger.debug("ErrorRegistry loaded successfully")
        except ImportError:
            logger.debug("ErrorRegistry not available (self_repair module not found)")
            _ERROR_REGISTRY = False
        except Exception as e:
            logger.debug(f"ErrorRegistry init failed: {e}")
            _ERROR_REGISTRY = False
    return _ERROR_REGISTRY if _ERROR_REGISTRY else None


def _get_dead_chunk_repair(
    enable_text_rewrite: bool = False,
    rewrite_conf_threshold: float = 0.7,
    memory_enabled: bool = False,
) -> Optional[Any]:
    """Lazy-load DeadChunkRepair for self-healing chunk recovery."""
    global _DEAD_CHUNK_REPAIR
    if (
        _DEAD_CHUNK_REPAIR is None
        or getattr(_DEAD_CHUNK_REPAIR, "enable_text_rewrite", None) != enable_text_rewrite
        or getattr(_DEAD_CHUNK_REPAIR, "rewrite_confidence_threshold", None) != rewrite_conf_threshold
        or getattr(_DEAD_CHUNK_REPAIR, "memory_enabled", None) != memory_enabled
    ):
        try:
            from self_repair.repair_loop import DeadChunkRepair
            registry = _get_error_registry()
            _DEAD_CHUNK_REPAIR = DeadChunkRepair(
                error_registry=registry,
                enable_text_rewrite=enable_text_rewrite,
                rewrite_confidence_threshold=rewrite_conf_threshold,
                memory_enabled=memory_enabled,
            )
            logger.debug("DeadChunkRepair loaded successfully")
        except ImportError:
            logger.debug("DeadChunkRepair not available (self_repair module not found)")
            _DEAD_CHUNK_REPAIR = False
        except Exception as e:
            logger.debug(f"DeadChunkRepair init failed: {e}")
            _DEAD_CHUNK_REPAIR = False
    return _DEAD_CHUNK_REPAIR if _DEAD_CHUNK_REPAIR else None


def _get_llama_reasoner() -> Optional[Any]:
    """Lazy-load LlamaReasoner to avoid import errors."""
    global _LLAMA_REASONER
    if _LLAMA_REASONER is None:
        try:
            from agents import LlamaReasoner
            _LLAMA_REASONER = LlamaReasoner()
            logger.debug("LlamaReasoner loaded successfully")
        except ImportError:
            logger.debug("LlamaReasoner not available (agents module not found)")
            _LLAMA_REASONER = False  # Mark as unavailable
        except Exception as e:
            logger.debug(f"LlamaReasoner init failed: {e}")
            _LLAMA_REASONER = False
    return _LLAMA_REASONER if _LLAMA_REASONER else None


# Ollama/LLM startup state
_OLLAMA_STATUS = None  # None = unchecked, dict = status


def _start_ollama_in_terminal() -> bool:
    """
    Start Ollama server in a visible terminal window.

    Tries multiple terminal emulators in order of preference.
    Returns True if successfully started, False otherwise.
    """
    import subprocess
    import shutil

    # Terminal emulators to try (in order of preference)
    terminal_commands = [
        # gnome-terminal (Ubuntu, GNOME)
        ["gnome-terminal", "--title=Ollama Server", "--", "ollama", "serve"],
        # konsole (KDE)
        ["konsole", "--title", "Ollama Server", "-e", "ollama", "serve"],
        # xfce4-terminal (XFCE)
        ["xfce4-terminal", "--title=Ollama Server", "-e", "ollama serve"],
        # xterm (fallback, usually available)
        ["xterm", "-title", "Ollama Server", "-e", "ollama", "serve"],
        # x-terminal-emulator (Debian/Ubuntu alternative)
        ["x-terminal-emulator", "-e", "ollama", "serve"],
    ]

    for cmd in terminal_commands:
        terminal_bin = cmd[0]
        if shutil.which(terminal_bin):
            try:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,  # Detach from parent process
                )
                logger.info(f"🖥️  Started Ollama server in {terminal_bin}")
                return True
            except Exception as e:
                logger.debug(f"Failed to start with {terminal_bin}: {e}")
                continue

    # No terminal emulator found, fall back to background process
    logger.info("No terminal emulator found, starting Ollama in background...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception as e:
        logger.warning(f"Failed to start Ollama: {e}")
        return False


def ensure_ollama_ready(model: str = "llama3.1:8b-instruct-q4_K_M") -> dict:
    """
    Ensure Ollama is ready for LLM-powered features (chunking, reasoning, etc).

    This runs at orchestrator startup to:
    1. Check if ollama Python package is installed
    2. Check if Ollama server is running (start in visible terminal if not)
    3. Check if required model is available (pull if not)

    Returns:
        dict with keys: available (bool), model (str), message (str)
    """
    global _OLLAMA_STATUS

    if _OLLAMA_STATUS is not None:
        return _OLLAMA_STATUS

    status = {"available": False, "model": model, "message": ""}

    # Step 1: Check if ollama Python package is installed
    try:
        import ollama
    except ImportError:
        status["message"] = (
            "❌ Ollama Python package not installed. "
            "Run: pip install ollama"
        )
        logger.warning(status["message"])
        _OLLAMA_STATUS = status
        return status

    # Step 2: Check if Ollama server is running
    try:
        models = ollama.list()
        logger.debug(f"Ollama server is running, {len(models.get('models', []))} models available")
    except Exception as e:
        # Try to start Ollama server in a visible terminal
        logger.info("🔄 Ollama server not running, attempting to start in terminal...")

        # First check if ollama binary is installed
        import shutil
        if not shutil.which("ollama"):
            status["message"] = (
                "❌ Ollama not installed. "
                "Install from: https://ollama.ai"
            )
            logger.warning(status["message"])
            _OLLAMA_STATUS = status
            return status

        # Start Ollama server
        if not _start_ollama_in_terminal():
            status["message"] = (
                "❌ Could not start Ollama server. "
                "Run manually: ollama serve"
            )
            logger.warning(status["message"])
            _OLLAMA_STATUS = status
            return status

        # Wait for server to start
        import time
        for i in range(15):  # Wait up to 15 seconds
            time.sleep(1)
            try:
                ollama.list()
                logger.info("✅ Ollama server started successfully")
                break
            except Exception:
                if i < 14:
                    logger.debug(f"Waiting for Ollama server... ({i+1}/15)")
                continue
        else:
            status["message"] = (
                "❌ Ollama server started but not responding. "
                "Check the Ollama terminal window for errors."
            )
            logger.warning(status["message"])
            _OLLAMA_STATUS = status
            return status

    # Step 3: Check if required model is available
    try:
        models = ollama.list()
        model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
        model_base = model.split(":")[0]

        if model_base not in model_names and model not in [m.get("name", "") for m in models.get("models", [])]:
            logger.info(f"🔄 Model '{model}' not found, pulling (this may take a few minutes)...")
            try:
                # Pull model (this can take a while)
                ollama.pull(model)
                logger.info(f"✅ Model '{model}' pulled successfully")
            except Exception as e:
                status["message"] = (
                    f"❌ Failed to pull model '{model}': {e}. "
                    f"Run manually: ollama pull {model}"
                )
                logger.warning(status["message"])
                _OLLAMA_STATUS = status
                return status
        else:
            logger.debug(f"Model '{model}' is available")
    except Exception as e:
        status["message"] = f"❌ Error checking models: {e}"
        logger.warning(status["message"])
        _OLLAMA_STATUS = status
        return status

    # All checks passed
    status["available"] = True
    status["message"] = f"✅ Ollama ready with model '{model}'"
    logger.info(status["message"])
    _OLLAMA_STATUS = status
    return status


def _store_phase_error(error_text: str) -> None:
    """Store error text for later AI analysis."""
    global _LAST_PHASE_ERROR
    _LAST_PHASE_ERROR = error_text


def _analyze_failure_with_llm(phase_num: int, file_id: str, error_output: Optional[str] = None) -> None:
    """Use LlamaReasoner to analyze a phase failure (if available).

    Args:
        phase_num: The phase that failed
        file_id: The file being processed
        error_output: The actual error text from the failure. If not provided,
                     falls back to _LAST_PHASE_ERROR global, but callers should
                     prefer passing explicit error context.
    """
    global _LAST_PHASE_ERROR

    # Use provided error or fall back to stored error
    error_text = error_output or _LAST_PHASE_ERROR
    if not error_text or len(error_text.strip()) < 10:
        logger.info("AI failure analysis skipped: insufficient error context for Phase %d", phase_num)
        return

    reasoner = _get_llama_reasoner()
    if not reasoner:
        logger.info("AI failure analysis unavailable (LlamaReasoner not loaded)")
        return

    try:
        context = {"phase": phase_num, "file_id": file_id}
        analysis = reasoner.analyze_failure(error_text, context=context)

        # Log the AI analysis
        logger.info("=" * 60)
        logger.info("AI FAILURE ANALYSIS (LlamaReasoner)")
        logger.info("=" * 60)
        logger.info(f"Root Cause: {analysis.root_cause}")
        logger.info(f"Category: {analysis.category} (confidence: {analysis.confidence:.0%})")
        logger.info(f"Severity: {analysis.severity}")
        logger.info(f"Suggested Fix: {analysis.suggested_fix}")
        if analysis.config_changes:
            logger.info(f"Config Changes: {analysis.config_changes}")
        if analysis.prevention_strategy:
            logger.info(f"Prevention: {analysis.prevention_strategy}")
        logger.info("=" * 60)

    except Exception as e:
        logger.warning("AI failure analysis failed: %s", e, exc_info=True)


def _record_chunk_failures(
    file_id: str,
    failed_chunks: List[str],
    engine: str,
    error_message: str = "TTS synthesis failed",
) -> None:
    """Record chunk failures to ErrorRegistry for tracking and future self-repair."""
    registry = _get_error_registry()
    if not registry:
        return

    for chunk_id in failed_chunks:
        try:
            registry.add_failure(
                chunk_id=chunk_id,
                file_id=file_id,
                category="tts_failure",
                message=f"{error_message} (engine: {engine})",
            )
            logger.debug(f"Recorded failure for {chunk_id} in ErrorRegistry")
        except Exception as e:
            logger.debug(f"Failed to record chunk failure: {e}")


try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich not available. Install with: pip install rich")

# Logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize Rich console
console = Console() if RICH_AVAILABLE else None

# Prefer Phase 1 hashing helper for reuse decisions when available
try:
    from phase1_validation.utils import compute_sha256 as _phase1_compute_sha256
except Exception:
    _phase1_compute_sha256 = None

ARCHIVE_ROOT = PROJECT_ROOT / "audiobooks"
PHASE4_AUDIO_DIR: Optional[Path] = None
_ORCHESTRATOR_CONFIG: Optional["OrchestratorConfig"] = None
RUN_SUMMARY: Dict[str, Any] = {
    "phase4_reused": False,
    "per_chunk_fallback_used": False,
    "tts_workers_used": None,
    "chunk_integrity_passed": None,
    "backup_subtitles_used": False,
    "budget_exceeded": False,
}
POLICY_RUNTIME_DIR = Path(".pipeline") / "policy_runtime"


def _policy_call(
    policy_engine: Optional[PolicyEngine],
    method: str,
    context: Dict[str, Any],
) -> None:
    """Invoke a policy hook defensively so orchestration never crashes."""
    if not policy_engine:
        return
    try:
        hook = getattr(policy_engine, method, None)
        if hook:
            hook(context)
    except Exception as exc:
        # Log at WARNING level when policy is actively guiding decisions
        learning_mode = getattr(policy_engine, "learning_mode", "observe")
        if learning_mode in ("enforce", "tune"):
            logger.warning(
                "Policy hook %s failed in %s mode: %s",
                method, learning_mode, exc, exc_info=True
            )
        else:
            logger.debug("Policy hook %s failed: %s", method, exc, exc_info=True)


def _timestamped_event_path(base_dir: Path) -> Path:
    """Return a unique, timestamped path for structured events."""
    base_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    return base_dir / f"{ts}.json"


def _log_decision_event(
    mode: str,
    overrides: Dict[str, Any],
    safety_ctx: Optional[Dict[str, Any]],
    run_id: Optional[str],
    source: str,
    allowed: bool,
) -> None:
    """Persist autonomy override decisions for auditability."""
    try:
        payload = {
            "mode": mode,
            "allowed": allowed,
            "overrides": overrides or {},
            "run_id": run_id,
            "source": source,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "safety": {
                "safe": (safety_ctx or {}).get("safety_eval", {}).get("safe", True) if safety_ctx else True,
                "escalation": (safety_ctx or {}).get("escalation", {}),
                "budget_allows": (safety_ctx or {}).get("budget_allows"),
                "policy_allows": (safety_ctx or {}).get("policy_allows"),
                "downgrade_reasons": (safety_ctx or {}).get("downgrade_reasons", []),
                "context": (safety_ctx or {}).get("context"),
            },
        }
        out_path = _timestamped_event_path(Path(".pipeline") / "autonomy" / "decisions")
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        logger.debug("Autonomy decision log write failed", exc_info=True)


def _load_readiness_inputs() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load evaluator summary and diagnostics (best-effort)."""
    summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
    evaluator_summary: Dict[str, Any] = {}
    if summary_path.exists():
        try:
            evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception:
            evaluator_summary = {}

    diagnostics_output: Dict[str, Any] = {}
    diag_dir = Path(".pipeline") / "diagnostics"
    latest_diag = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if latest_diag:
        try:
            diagnostics_output = json.loads(latest_diag[0].read_text(encoding="utf-8"))
        except Exception:
            diagnostics_output = {}
    return evaluator_summary, diagnostics_output


def _evaluate_autonomy_safety(
    orchestrator_config: "OrchestratorConfig",
    recommendation: Optional[Dict[str, Any]],
    *,
    run_id: Optional[str] = None,
    context: str = "runtime",
) -> Dict[str, Any]:
    """
    Run the safety chain in the required order:
    readiness -> stability_bounds -> drift_detection -> safety_envelope ->
    safety_escalation -> budget -> policy -> overrides.
    """
    autonomy_cfg = orchestrator_config.autonomy
    rec_changes: Dict[str, Any] = {}
    confidence = 0.0
    if recommendation:
        rec_changes = (
            recommendation.get("autonomous_recommendations", {}).get("changes", {})
            or recommendation.get("suggested_changes", {})
            or {}
        )
        confidence = float(
            recommendation.get("autonomous_recommendations", {}).get("confidence", recommendation.get("confidence", 0.0))
            or 0.0
        )

    readiness_report: Dict[str, Any] = {}
    if autonomy_cfg.readiness_checks.get("enable", False):
        try:
            from autonomy import readiness, reinforcement
            from policy_engine.policy_engine import get_benchmark_history

            evaluator_summary, diagnostics_output = _load_readiness_inputs()
            bench = get_benchmark_history()
            recent_rewards = reinforcement.load_recent_rewards()
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            readiness_report = readiness.check_readiness(
                evaluator_summary,
                diagnostics_output,
                recent_rewards,
                bench,
                autonomy_cfg.readiness_checks,
            )
            out_dir = Path(".pipeline") / "policy_runtime"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"autonomy_readiness_{ts}.json").write_text(
                json.dumps(readiness_report, indent=2),
                encoding="utf-8",
            )
        except Exception:
            readiness_report = {}

    stability_result: Dict[str, Any] = {}
    filtered_changes = dict(rec_changes)
    if autonomy_cfg.enable_stability_bounds and rec_changes:
        try:
            stability_result = check_stability_bounds(rec_changes, {}, autonomy_cfg)
            if stability_result.get("violations"):
                log_safety_event("stability_violation", {"violations": stability_result.get("violations")})
            if stability_result.get("filtered_overrides"):
                filtered_changes = stability_result["filtered_overrides"]
        except Exception:
            stability_result = {}

    drift_info: Dict[str, Any] = {}
    if autonomy_cfg.enable_drift_monitoring:
        try:
            from autonomy import memory_store  # type: ignore
        except Exception:
            memory_store = None  # type: ignore
        run_history = memory_store.load_run_history(limit=50) if memory_store and hasattr(memory_store, "load_run_history") else []
        try:
            drift_info = detect_drift(run_history, {})
            if drift_info.get("drift_detected"):
                log_safety_event("drift_detected", drift_info)
        except Exception:
            drift_info = {}

    safety_eval = {"safe": True, "blocked_reasons": []}
    if autonomy_cfg.enable_safety_envelope:
        try:
            safety_eval = apply_safety_envelope(readiness_report or {}, stability_result, drift_info, autonomy_cfg)
        except Exception:
            safety_eval = {"safe": True, "blocked_reasons": []}

    escalation_result: Dict[str, Any] = {"lockout": False}
    if autonomy_cfg.enable_safety_escalation:
        try:
            safety_state_path = Path(".pipeline") / "policy_runtime" / "safety_state.json"
            state = load_safety_state(safety_state_path)
            escalation_result = evaluate_escalation(state, drift_info, stability_result, autonomy_cfg)
            if escalation_result.get("updated_state") is not None:
                write_safety_state(safety_state_path, escalation_result["updated_state"])
            if escalation_result.get("lockout"):
                log_safety_event("escalation_lockout", escalation_result)
        except Exception:
            escalation_result = {"lockout": False}

    budgeted_changes = dict(filtered_changes)
    budget_allows = True
    if filtered_changes and autonomy_cfg.enable_budget:
        try:
            from autonomy.autonomy_budget import enforce_budget

            budgeted = enforce_budget({"suggested_changes": filtered_changes, "confidence": confidence}, autonomy_cfg)
            budgeted_changes = budgeted.get("suggested_changes") or {}
            budget_allows = bool(budgeted_changes) or not filtered_changes
        except Exception:
            budget_allows = False

    policy_filtered_changes = dict(budgeted_changes)
    policy_allows = True
    if budgeted_changes and autonomy_cfg.enable_policy_engine:
        try:
            from autonomy.autonomy_policy import check_policy

            policy_filtered_changes = check_policy(budgeted_changes)
            policy_allows = bool(policy_filtered_changes)
        except Exception:
            policy_allows = False

    allow_overrides = (
        safety_eval.get("safe", True)
        and not escalation_result.get("lockout")
        and (budget_allows or not filtered_changes)
        and (policy_allows or not budgeted_changes)
    )
    autonomy_mode = autonomy_cfg.mode
    downgrade_reasons: List[str] = []
    if not safety_eval.get("safe", True):
        autonomy_mode = "supervised"
        downgrade_reasons.append("safety_envelope_block")
    if escalation_result.get("lockout"):
        autonomy_mode = "supervised"
        downgrade_reasons.append("escalation_lockout")

    if downgrade_reasons:
        log_safety_event(
            "autonomy_downgrade",
            {
                "reasons": downgrade_reasons,
                "context": context,
                "run_id": run_id,
                "safety_eval": safety_eval,
                "escalation": escalation_result,
            },
        )
    elif not allow_overrides:
        log_safety_event(
            "autonomy_override_blocked",
            {
                "context": context,
                "budget_allows": budget_allows,
                "policy_allows": policy_allows,
                "run_id": run_id,
            },
        )

    return {
        "autonomy_mode": autonomy_mode,
        "readiness": readiness_report,
        "stability": stability_result,
        "drift": drift_info,
        "safety_eval": safety_eval,
        "escalation": escalation_result,
        "budget_allows": budget_allows,
        "policy_allows": policy_allows,
        "filtered_overrides": policy_filtered_changes if allow_overrides else {},
        "allow_overrides": allow_overrides,
        "downgrade_reasons": downgrade_reasons,
        "context": context,
    }


def _phase_entry_snapshot(state: PipelineState, phase_key: str, file_id: str) -> Dict[str, Any]:
    snapshot = read_state_snapshot(state, warn=False)
    phase_block = snapshot.get(phase_key, {}) or {}
    files = phase_block.get("files", {}) or {}
    entry = files.get(file_id)
    if isinstance(entry, dict):
        return entry
    fallback: Dict[str, Any] = {}
    for key in ("status", "errors", "metrics", "timestamps"):
        value = phase_block.get(key)
        if value:
            fallback[key] = value
    return fallback


def _build_policy_context(
    phase_key: str,
    file_id: str,
    pipeline_json: Path,
    *,
    status: str,
    event: str,
    state: PipelineState,
    duration_ms: Optional[float] = None,
    include_snapshot: bool = False,
    metrics: Optional[Dict[str, Any]] = None,
    errors: Optional[List[Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    timestamp = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    context: Dict[str, Any] = {
        "timestamp": timestamp,
        "phase": phase_key,
        "file_id": file_id,
        "status": status,
        "event": event,
        "pipeline_json": str(pipeline_json),
    }
    if duration_ms is not None:
        context["duration_ms"] = duration_ms
    normalized_errors: Optional[List[str]] = None
    if errors:
        normalized_errors = [str(err) for err in errors if err]
        if normalized_errors:
            context["errors"] = normalized_errors
    if metrics is not None:
        context["metrics"] = metrics
    if extra:
        context["extra"] = extra
    if include_snapshot:
        snapshot = _phase_entry_snapshot(state, phase_key, file_id)
        if snapshot:
            context["phase_snapshot"] = snapshot
            if "metrics" not in context and isinstance(snapshot.get("metrics"), dict):
                context["metrics"] = snapshot["metrics"]
            snapshot_errors = snapshot.get("errors")
            if snapshot_errors and "errors" not in context:
                context["errors"] = snapshot_errors
    return context


def _prepare_phase3_config_override(
    phase_dir: Path,
    chunk_override: Dict[str, Any],
    run_id: str,
) -> Optional[Path]:
    """Create a temporary config.yaml with adjusted chunk sizes."""
    base_config = phase_dir / "config.yaml"
    if not base_config.exists():
        logger.warning("Phase 3 override skipped: config.yaml not found in %s", phase_dir)
        return None
    delta = chunk_override.get("delta_percent")
    try:
        delta_value = float(delta)
    except (TypeError, ValueError):
        logger.warning("Phase 3 override skipped: invalid delta %s", delta)
        return None
    delta_value = max(-20.0, min(20.0, delta_value))
    if delta_value == 0:
        return None
    factor = 1.0 + (delta_value / 100.0)
    try:
        with base_config.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
    except Exception as exc:
        logger.warning("Phase 3 override skipped: cannot read config (%s)", exc)
        return None
    changed = False
    for key in (
        "chunk_min_words",
        "chunk_max_words",
        "chunk_min_chars",
        "chunk_max_chars",
    ):
        value = config.get(key)
        if isinstance(value, (int, float)):
            new_value = max(1, int(round(value * factor)))
            config[key] = new_value
            changed = True
    if not changed:
        return None
    POLICY_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    override_path = POLICY_RUNTIME_DIR / f"phase3_config_{run_id}.yaml"
    try:
        with override_path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(config, handle, sort_keys=False)
    except Exception as exc:
        logger.warning("Phase 3 override skipped: cannot write override config (%s)", exc)
        return None
    logger.info(
        "Phase 3 chunk size override applied (%+.1f%% -> %s)",
        delta_value,
        override_path,
    )
    return override_path


def _pop_phase_duration(timer_map: Dict[str, float], phase_key: str) -> Optional[float]:
    started = timer_map.pop(phase_key, None)
    if started is None:
        return None
    return max((time.perf_counter() - started) * 1000.0, 0.0)


def _log_policy_advice(
    policy_engine: Optional[PolicyEngine],
    context: Dict[str, Any],
    phase_label: str,
    file_id: str,
) -> None:
    if not policy_engine:
        return
    advice = policy_engine.advise(context)
    if not advice:
        return

    suggestions = advice.get("suggestions") or []
    if suggestions:
        for entry in suggestions:
            suggestion_type = entry.get("type")
            payload = entry.get("payload")
            confidence = entry.get("confidence")
            logger.info(
                "Policy %s suggestion for %s (%s) [confidence=%.2f]: %s",
                suggestion_type,
                file_id,
                phase_label,
                (float(confidence) if isinstance(confidence, (int, float)) else 0.0),
                payload,
            )
    legacy = {key: value for key, value in advice.items() if key not in {"suggestions", "telemetry"}}
    if legacy:
        logger.info(
            "Policy recommendations for %s (%s): %s",
            file_id,
            phase_label,
            legacy,
        )

    telemetry = advice.get("telemetry") or {}
    if telemetry:
        rtf_stats = telemetry.get("rtf_stats") or {}
        fallback = telemetry.get("engine_fallback_rates") or {}
        hallu = telemetry.get("hallucination_stats") or {}
        summary_parts = []
        recent_rt = rtf_stats.get("recent_avg")
        if isinstance(recent_rt, (int, float)):
            summary_parts.append(f"RT avg {recent_rt:.2f}x")
        recent_fb = (fallback.get("overall") or {}).get("recent_rate")
        if isinstance(recent_fb, (int, float)):
            summary_parts.append(f"fallback {recent_fb*100:.1f}%")
        recent_hallu = hallu.get("recent_total")
        if isinstance(recent_hallu, int) and recent_hallu:
            summary_parts.append(f"{recent_hallu} hallucination alerts")
        if summary_parts:
            logger.info(
                "Policy telemetry for %s (%s): %s",
                file_id,
                phase_label,
                ", ".join(summary_parts),
            )
        else:
            logger.debug(
                "Policy telemetry for %s (%s): %s",
                file_id,
                phase_label,
                telemetry,
            )


class SubtitleConfig(BaseModel):
    enable_backup_align: bool = True
    max_drift_sec: float = 2.0
    min_coverage_ratio: float = 0.95


class TTSEngineConfig(BaseModel):
    primary: str = "xtts"
    secondary: Optional[str] = "kokoro"


class PhaseTimeouts(BaseModel):
    """Per-phase timeout configuration in seconds."""

    phase1: int = 18000  # 5 hours for validation
    phase2: int = 18000  # 5 hours for extraction
    phase3: int = 600    # 10 minutes for chunking
    phase4: int = 28800  # 8 hours for TTS (large books)
    phase5: int = 1800   # 30 minutes for enhancement
    phase5_5: int = 3600  # 60 minutes for subtitles
    poetry_install: int = 300  # 5 minutes for dependency install

    def get(self, phase_num: int) -> int:
        """Get timeout for a specific phase."""
        return getattr(self, f"phase{phase_num}", 18000)


class AutonomyConfig(BaseModel):
    enable: bool = False
    supervised_mode: bool = True
    global_settings: Dict[str, Any] = Field(default_factory=dict, alias="global")
    enable_self_repair: bool = False
    use_reasoner: bool = False
    planner_mode: str = "disabled"  # disabled | recommend_only | enforce (future)
    memory_enabled: bool = False
    memory_summarization: str = "periodic"  # periodic | off
    mode: str = "disabled"  # disabled | recommend_only | supervised | autonomous (not implemented)
    supervised_threshold: float = 0.85
    policy_kernel_debug: bool = False
    policy_kernel_enabled: bool = False
    enable_policy_engine: bool = False
    enable_engine_retry: bool = False
    enable_experiments: bool = False
    enable_memory_feedback: bool = False
    enable_stability_profiles: bool = False
    enable_confidence_calibration: bool = False
    enable_self_evaluation: bool = False
    enable_planner_feedback: bool = False
    enable_self_review: bool = False
    enable_rewards: bool = False
    enable_policy_limits: bool = False
    enable_budget: bool = False
    enable_long_horizon: bool = False
    enable_long_horizon_learning: bool = False
    enable_forecasting: bool = False
    enable_drift_monitoring: bool = False
    enable_stability_bounds: bool = False
    enable_safety_envelope: bool = False
    enable_safety_escalation: bool = False
    enable_long_horizon_profiles: bool = False
    enable_trend_modeling: bool = False
    stability_bounds: Dict[str, Any] = Field(default_factory=dict)
    escalation: Dict[str, Any] = Field(default_factory=dict)
    profiles: Dict[str, Any] = Field(default_factory=dict)
    readiness_checks: Dict[str, Any] = Field(default_factory=dict)
    budget: Dict[str, Any] = Field(default_factory=dict)
    self_eval: Dict[str, Any] = Field(default_factory=dict)


class SelfRepairConfig(BaseModel):
    enable_text_rewrite: bool = False
    rewrite_confidence_threshold: float = 0.7
    enable_repair_loop: bool = False
    enable_log_parser: bool = False
    repair_confidence_threshold: float = 0.85
    enable_engine_retry: bool = False
    retry_confidence_threshold: float = 0.85


class ReasoningConfig(BaseModel):
    enable_evaluator: bool = False
    enable_diagnostics: bool = False


class ExperimentsConfig(BaseModel):
    enable: bool = False
    limit_per_run: int = 1
    allowed: List[str] = Field(default_factory=lambda: ["chunk_size", "engine_preference", "rewrite_policy"])
    dry_run: bool = True


class DashboardConfig(BaseModel):
    enable_data_api: bool = False


class GenreConfig(BaseModel):
    enable_classifier: bool = False
    use_llama: bool = False


class OrchestratorConfig(BaseModel):
    pipeline_path: Path = Field(default=Path("../pipeline.json"), alias="pipeline_json")
    phases_to_run: List[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    phase_timeout: Optional[int] = None  # Legacy: global override
    phase_timeouts: PhaseTimeouts = Field(default_factory=PhaseTimeouts)  # Per-phase timeouts
    resume_enabled: bool = True
    log_level: str = "INFO"
    log_file: Optional[str] = None
    pipeline_mode: str = "commercial"
    tts_engine: str = "xtts"
    phase4_reuse_enabled: bool = True
    min_mos_for_reuse: Optional[float] = None
    strict_chunk_integrity: bool = True
    max_tts_workers: int = 1
    per_chunk_fallback: bool = True
    tts_engines: TTSEngineConfig = Field(default_factory=TTSEngineConfig)
    prefer_shell_tts_execution: bool = False
    global_time_budget_sec: Optional[int] = None
    subtitles: SubtitleConfig = Field(default_factory=SubtitleConfig)
    policy_engine: Dict[str, Any] = Field(default_factory=lambda: {"logging": True, "learning_mode": "observe"})
    self_repair: SelfRepairConfig = Field(default_factory=SelfRepairConfig)
    autonomy: AutonomyConfig = Field(default_factory=AutonomyConfig)
    reasoning: ReasoningConfig = Field(default_factory=ReasoningConfig)
    experiments: ExperimentsConfig = Field(default_factory=ExperimentsConfig)
    genre: GenreConfig = Field(default_factory=GenreConfig)
    dashboard: DashboardConfig = Field(default_factory=DashboardConfig)
    rewriter: Dict[str, Any] = Field(default_factory=dict)
    adaptive_chunking: Dict[str, Any] = Field(default_factory=dict)
    patches: Dict[str, Any] = Field(default_factory=dict)
    introspection: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    benchmark: Dict[str, Any] = Field(default_factory=dict)
    ui: Dict[str, Any] = Field(default_factory=dict)
    phaseA: Dict[str, Any] = Field(default_factory=dict)
    phaseB: Dict[str, Any] = Field(default_factory=dict)
    phaseC: Dict[str, Any] = Field(default_factory=dict)
    phaseAA: Dict[str, Any] = Field(default_factory=dict)
    phaseQ_self_eval: Dict[str, Any] = Field(default_factory=dict)
    phaseQ_self_evaluation: Dict[str, Any] = Field(default_factory=dict)
    phaseR: Dict[str, Any] = Field(default_factory=dict)
    phaseS: Dict[str, Any] = Field(default_factory=dict)
    phaseT: Dict[str, Any] = Field(default_factory=dict)
    consistency: Dict[str, Any] = Field(default_factory=dict)
    phaseU: Dict[str, Any] = Field(default_factory=dict)
    phaseV: Dict[str, Any] = Field(default_factory=dict)
    phaseW: Dict[str, Any] = Field(default_factory=dict)
    phaseX: Dict[str, Any] = Field(default_factory=dict)
    phaseY: Dict[str, Any] = Field(default_factory=dict)
    phaseZ: Dict[str, Any] = Field(default_factory=dict)
    phaseAB: Dict[str, Any] = Field(default_factory=dict)
    phaseAC: Dict[str, Any] = Field(default_factory=dict)
    phaseAD: Dict[str, Any] = Field(default_factory=dict)
    phaseAE: Dict[str, Any] = Field(default_factory=dict)
    phaseAF: Dict[str, Any] = Field(default_factory=dict)
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    phaseJ: Dict[str, Any] = Field(default_factory=dict)
    phaseK: Dict[str, Any] = Field(default_factory=dict)
    phaseL: Dict[str, Any] = Field(default_factory=dict)
    phaseM: Dict[str, Any] = Field(default_factory=dict)
    phaseN: Dict[str, Any] = Field(default_factory=dict)
    phaseO: Dict[str, Any] = Field(default_factory=dict)
    research: Dict[str, Any] = Field(default_factory=dict)
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    def get_phase_timeout(self, phase_num: int) -> int:
        """Get timeout for a phase, respecting legacy global override."""
        if self.phase_timeout is not None:
            return self.phase_timeout
        return self.phase_timeouts.get(phase_num)


def get_orchestrator_config() -> OrchestratorConfig:
    """Load phase6 config.yaml once and validate with Pydantic."""
    global _ORCHESTRATOR_CONFIG
    if isinstance(_ORCHESTRATOR_CONFIG, OrchestratorConfig):
        return _ORCHESTRATOR_CONFIG

    config_path = Path(__file__).with_name("config.yaml")
    data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception as exc:
            logger.warning("Failed to read orchestrator config (%s); using defaults.", exc)
    if "pipeline_path" not in data and "pipeline_json" not in data:
        data["pipeline_json"] = "../pipeline.json"

    try:
        _ORCHESTRATOR_CONFIG = OrchestratorConfig(**data)
    except ValidationError as exc:
        logger.warning("Invalid orchestrator config, using defaults. Details: %s", exc)
        _ORCHESTRATOR_CONFIG = OrchestratorConfig()
    return _ORCHESTRATOR_CONFIG


def get_pipeline_mode() -> str:
    return get_orchestrator_config().pipeline_mode.lower()


def get_tts_engine() -> str:
    return get_orchestrator_config().tts_engine.lower()


def set_phase4_audio_dir(audio_dir: Path) -> None:
    global PHASE4_AUDIO_DIR
    PHASE4_AUDIO_DIR = audio_dir.resolve()


def print_status(message: str, style: str = "bold") -> None:
    """Print status message with Rich or fallback to print."""
    if console:
        console.print(message, style=style)
    else:
        print(message)


def print_panel(content: str, title: str = "", style: str = "") -> None:
    """Print panel with Rich or fallback."""
    if console:
        console.print(Panel(content, title=title, style=style))
    else:
        print(f"\n{'='*60}")
        if title:
            print(f"{title}")
            print("=" * 60)
        print(content)
        print("=" * 60 + "\n")


def compute_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA256 for reuse decisions."""
    if _phase1_compute_sha256:
        return _phase1_compute_sha256(path)
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk_size), b""):
            sha.update(block)
    return sha.hexdigest()


def compute_chunk_text_hash(chunk_paths: List[str]) -> str:
    """Hash concatenated chunk text to enable Phase 4 reuse decisions."""
    sha = hashlib.sha256()
    for raw_path in chunk_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = path.resolve()
        if not path.exists():
            continue
        try:
            sha.update(path.read_bytes())
        except Exception as exc:  # best-effort hashing
            logger.warning("Could not hash %s for reuse check: %s", path, exc)
    return sha.hexdigest()


def play_sound(success: bool = True) -> None:
    """Play a short audible cue on Windows; no-op elsewhere."""
    try:
        if sys.platform != "win32":
            return
        import winsound

        if success:
            # Two quick beeps: success
            winsound.Beep(1000, 200)
            winsound.Beep(1300, 200)
        else:
            # Lower, longer tone: failure
            winsound.Beep(400, 600)
    except Exception as exc:  # If sound is unavailable, ignore
        logger.debug("Sound playback skipped: %s", exc)


def humanize_title(file_id: str) -> str:
    """Convert file_id or filename into a readable title."""
    name = Path(file_id).stem
    name = re.sub(r"[_\-]+", " ", name).strip()
    return name.title() if name else "Audiobook"


def resolve_phase5_audiobook_path(file_id: str, pipeline_json: Path, phase5_dir: Path) -> Path:
    """Locate the final audiobook path recorded in pipeline.json (with fallbacks)."""
    audiobook_path: Optional[Path] = None
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        pipeline_data = state.read()
    except Exception as exc:
        logger.warning(f"Failed to read pipeline.json for archive lookup: {exc}")
        pipeline_data = {}

    phase5_data = pipeline_data.get("phase5", {}) or {}
    raw_path = phase5_data.get("output_file")

    if not raw_path:
        phase5_files = phase5_data.get("files", {}) or {}
        if phase5_files:
            candidate_key = file_id if file_id in phase5_files else next(iter(phase5_files))
            entry = phase5_files.get(candidate_key, {})
            raw_path = entry.get("path") or entry.get("output_file")

    if raw_path:
        audiobook_path = Path(raw_path)
        if not audiobook_path.is_absolute():
            audiobook_path = (phase5_dir / audiobook_path).resolve()
    else:
        # Try multiple fallback paths based on Phase 5 output structure:
        # 1. processed/{file_id}/mp3/audiobook.mp3 (new per-file structure)
        # 2. processed/mp3/audiobook.mp3 (single-file structure)
        # 3. processed/audiobook.mp3 (legacy structure)
        fallback_paths = [
            phase5_dir / "processed" / file_id / "mp3" / "audiobook.mp3",
            phase5_dir / "processed" / "mp3" / "audiobook.mp3",
            phase5_dir / "processed" / "audiobook.mp3",
        ]
        for fallback in fallback_paths:
            if fallback.exists():
                audiobook_path = fallback.resolve()
                break
        else:
            # Return the most likely path even if it doesn't exist (for error reporting)
            audiobook_path = fallback_paths[0].resolve()

    return audiobook_path


def concat_phase5_from_existing(phase_dir: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Build final MP3 from existing enhanced WAVs without re-running enhancement.
    """
    processed_dir = phase_dir / "processed"
    wavs = sorted(processed_dir.glob("enhanced_*.wav"))
    if not wavs:
        logger.error("Concat-only mode: no enhanced_*.wav files found.")
        return False

    list_file = phase_dir / "temp_concat_list.txt"
    try:
        list_file.write_text(
            "\n".join([f"file '{p.resolve().as_posix()}'" for p in wavs]),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.error("Failed to write concat list: %s", exc)
        return False

    mp3_path = processed_dir / "audiobook.mp3"
    if mp3_path.exists():
        mp3_path.unlink()

    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "warning",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-ac",
        "1",
        "-ar",
        "24000",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-id3v2_version",
        "3",
        "-metadata",
        f"title={humanize_title(file_id)}",
        "-metadata",
        f"artist={file_id}",
        str(mp3_path),
    ]

    result = subprocess.run(cmd, cwd=str(phase_dir), capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(
            "Concat-only ffmpeg failed (exit %s): %s",
            result.returncode,
            result.stderr[-1000:],
        )
        return False

    logger.info("Concat-only MP3 created at %s", mp3_path)

    # Update pipeline.json
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        with state.transaction() as txn:
            phase5 = txn.data.setdefault("phase5", {"status": "partial", "files": {}})
            files = phase5.setdefault("files", {})
            entry = files.get(file_id, {})
            entry.update(
                {
                    "status": "success",
                    "output_file": str(mp3_path),
                    "chunks_completed": len(wavs),
                    "total_chunks": len(wavs),
                    "audio_dir": str(processed_dir),
                }
            )
            files[file_id] = entry
            phase5["status"] = "success"
        logger.info("pipeline.json updated for concat-only run")
    except Exception as exc:
        logger.warning("Failed to update pipeline.json after concat-only: %s", exc)

    try:
        list_file.unlink()
    except Exception:
        pass

    return True


def archive_final_audiobook(file_id: str, pipeline_json: Path) -> None:
    """Save a copy of the final audiobook that survives Phase 5 cleanup."""
    phase5_dir = find_phase_dir(5)
    if not phase5_dir:
        logger.warning("Cannot archive audiobook: Phase 5 directory not found")
        return

    source_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)

    if not source_path.exists():
        logger.warning(f"Archive skipped: audiobook not found at {source_path}")
        return

    title = humanize_title(file_id)
    archive_dir = ARCHIVE_ROOT / title
    archive_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest_path = archive_dir / f"{title}_{timestamp}.mp3"

    try:
        shutil.copy2(source_path, dest_path)
        # Also copy canonical name (audiobook.mp3) in the title folder
        canonical_path = archive_dir / "audiobook.mp3"
        shutil.copy2(source_path, canonical_path)
        logger.info(f"Archived final audiobook to {dest_path} and {canonical_path}")
    except Exception as exc:
        logger.warning(f"Failed to archive audiobook copy: {exc}")


def get_clean_env_for_poetry() -> Dict[str, str]:
    """
    Create a clean environment for Poetry subprocess calls.

    When the orchestrator runs in its own Poetry virtualenv, os.environ contains
    Poetry/virtualenv variables that interfere with Poetry's ability to detect
    and activate the correct virtualenv for phase subdirectories.

    This function creates a clean environment by removing Poetry-specific variables
    while preserving necessary system variables.

    Returns:
        Clean environment dict suitable for subprocess.run(env=...)
    """
    env = os.environ.copy()

    # Remove Poetry and virtualenv variables that interfere with Poetry's detection
    vars_to_remove = [
        "VIRTUAL_ENV",  # Points to current virtualenv
        "POETRY_ACTIVE",  # Indicates Poetry is active
        "PYTHONHOME",  # Can override Python location
        "_OLD_VIRTUAL_PATH",  # Backup of PATH before virtualenv activation
        "_OLD_VIRTUAL_PYTHONHOME",  # Backup of PYTHONHOME
    ]

    for var in vars_to_remove:
        env.pop(var, None)

    # Clean PATH to remove current virtualenv's Scripts/bin directory
    # This allows Poetry to add the correct virtualenv's Scripts/bin
    if "PATH" in env:
        path_parts = env["PATH"].split(os.pathsep)
        # Filter out paths containing current virtualenv indicators
        clean_path_parts = [
            p for p in path_parts if not any(indicator in p.lower() for indicator in ["virtualenvs", ".venv", "poetry"])
        ]
        env["PATH"] = os.pathsep.join(clean_path_parts)

    return env


def check_conda_environment(env_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if Conda environment exists and is accessible.

    Returns:
        (exists: bool, error_message: Optional[str])
    """
    try:
        # Check if conda is available
        result = subprocess.run(["conda", "--version"], capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            return (
                False,
                "Conda not found. Install Miniconda or Anaconda first.",
            )

        # Check if environment exists
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if env_name not in result.stdout:
            error_msg = (
                f"Conda environment '{env_name}' not found.\n\n"
                f"Create it with:\n"
                f"  cd phase4_tts\n"
                f"  conda env create -f environment.yml\n"
                f"  conda activate {env_name}\n"
                f"  pip install -r envs/requirements_xtts.txt\n"
                f"  pip install kokoro-onnx piper-tts"
            )
            return False, error_msg

        # Verify environment can be activated
        test_cmd = ["conda", "run", "-n", env_name, "python", "--version"]
        result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return False, f"Cannot activate '{env_name}': {result.stderr}"

        logger.info(f"OK Conda environment '{env_name}' is ready")
        return True, None

    except FileNotFoundError:
        error_msg = (
            "Conda not found in PATH.\n\n"
            "Install Miniconda from: https://docs.conda.io/en/latest/miniconda.html\n"
            "Or add Conda to PATH if already installed."
        )
        return False, error_msg
    except subprocess.TimeoutExpired:
        return False, "Conda command timed out. Check your Conda installation."
    except Exception as e:
        return False, f"Conda check failed: {str(e)}"


def collect_file_phase_view(data: Dict[str, Any], file_id: str) -> Dict[str, Any]:
    """Return a phase-indexed view of the pipeline for a given file_id."""
    phases = {}
    for phase_key, block in data.items():
        if not isinstance(block, dict):
            continue
        files = block.get("files") or {}
        if isinstance(files, dict) and file_id in files:
            phases[phase_key] = files[file_id]
    return phases


def build_file_phase_view(state: PipelineState, file_id: str) -> Dict[str, Any]:
    """Read pipeline.json via PipelineState and build a per-file, phase-indexed view."""
    snapshot = read_state_snapshot(state, warn=False)
    return collect_file_phase_view(snapshot, file_id)


def read_state_snapshot(state: PipelineState, *, warn: bool = True) -> Dict[str, Any]:
    """Safely read the canonical pipeline state."""
    try:
        return state.read()
    except StateError as exc:
        if warn:
            logger.warning("Failed to read pipeline state: %s", exc)
        return {}
    except Exception as exc:  # pragma: no cover - defensive logging
        if warn:
            logger.warning("Unexpected pipeline state error: %s", exc)
        return {}


def should_skip_phase2(file_path: Path, file_id: str, state: PipelineState) -> bool:
    """Decide whether to skip Phase 2 based on existing extraction hash.

    Uses Phase 2 recorded `source_hash` or falls back to Phase 1 hash.
    """
    pipeline_data = read_state_snapshot(state, warn=False)
    phase2_entry = pipeline_data.get("phase2", {}).get("files", {}).get(file_id, {})
    if phase2_entry.get("status") != "success":
        return False

    extracted_path = (
        phase2_entry.get("extracted_text_path") or phase2_entry.get("path") or phase2_entry.get("output_file")
    )
    if not extracted_path or not Path(extracted_path).exists():
        return False

    recorded_hash = phase2_entry.get("source_hash")
    phase1_hash = pipeline_data.get("phase1", {}).get("files", {}).get(file_id, {}).get("hash")

    # If no hash recorded, still allow skip to honor prior success (legacy runs)
    if not recorded_hash and not phase1_hash:
        logger.info("Phase 2 reuse: found existing success (no hash recorded); skipping.")
        return True

    try:
        current_hash = compute_sha256(file_path)
    except Exception as exc:
        logger.warning("Phase 2 reuse: failed to hash source (%s); will run Phase 2.", exc)
        return False

    expected_hash = recorded_hash or phase1_hash
    if expected_hash and current_hash == expected_hash:
        logger.info("Phase 2 reuse: hash match (%s); skipping.", file_id)
        return True

    logger.info("Phase 2 reuse: source hash changed; re-running Phase 2.")
    return False


def should_skip_phase3(file_id: str, state: PipelineState) -> bool:
    """Decide whether to skip Phase 3 based on chunking/text hash match."""
    data = read_state_snapshot(state, warn=False)
    phase3_entry = data.get("phase3", {}).get("files", {}).get(file_id, {})
    if phase3_entry.get("status") != "success":
        return False

    chunk_paths = phase3_entry.get("chunk_paths") or []
    if not chunk_paths or not all(Path(p).exists() for p in chunk_paths):
        return False

    # Prefer Phase 3 source_hash, else recompute from Phase 2 text
    recorded_hash = phase3_entry.get("source_hash")
    if not recorded_hash:
        text_path = phase3_entry.get("text_path") or data.get("phase2", {}).get("files", {}).get(file_id, {}).get(
            "extracted_text_path"
        )
        if not text_path or not Path(text_path).exists():
            return False
        try:
            recorded_hash = compute_sha256(Path(text_path))
            # Note: we do not persist this here; Phase 3 main writes it on next run.
        except Exception as exc:
            logger.warning(
                "Phase 3 reuse: failed to hash text (%s); will run Phase 3.",
                exc,
            )
            return False

    text_path = phase3_entry.get("text_path") or data.get("phase2", {}).get("files", {}).get(file_id, {}).get(
        "extracted_text_path"
    )
    if not text_path or not Path(text_path).exists():
        return False

    try:
        current_hash = compute_sha256(Path(text_path))
    except Exception as exc:
        logger.warning(
            "Phase 3 reuse: failed to hash current text (%s); will run Phase 3.",
            exc,
        )
        return False

    if recorded_hash and recorded_hash == current_hash:
        logger.info("Phase 3 reuse: hash match (%s); skipping.", file_id)
        return True

    logger.info("Phase 3 reuse: text hash changed; re-running Phase 3.")
    return False


def check_phase_status(state: PipelineState, phase_num: int, file_id: str) -> str:
    """
    Check status of a phase for a specific file.

    Returns:
        "success", "failed", "partial", or "pending"
    """
    snapshot = read_state_snapshot(state, warn=False)
    phase_key = f"phase{phase_num}"
    phase_data = snapshot.get(phase_key, {})
    files = phase_data.get("files", {})

    if file_id in files:
        return files[file_id].get("status", "pending")

    # Fall back to overall status if no file-specific data exists
    overall_status = phase_data.get("status")
    if overall_status in {"success", "partial", "failed"}:
        return overall_status

    return "pending"


def find_phase_dir(phase_num: int, variant: Optional[str] = None) -> Optional[Path]:
    """Find directory for a phase number.

    Args:
        phase_num: Phase number (1-5)
        variant: Optional variant (e.g., 'xtts' for phase3b-xtts-chunking)
    """
    project_root = PROJECT_ROOT

    mapping = {
        1: "phase1-validation",
        2: "phase2-extraction",
        3: "phase3-chunking",
        4: "phase4_tts",
        5: "phase5_enhancement",
    }
    phase_name = mapping.get(phase_num)

    if not phase_name:
        return None

    phase_dir = project_root / phase_name
    if phase_dir.exists():
        return phase_dir

    logger.error(f"Phase {phase_num} directory not found: {phase_dir}")
    return None


def load_phase3_chunks(file_id: str, pipeline_json: Path) -> Tuple[str, List[str]]:
    """Return the resolved Phase 3 key and its chunk paths."""
    state = PipelineState(pipeline_json, validate_on_read=False)
    pipeline = state.read()
    phase3_files = pipeline.get("phase3", {}).get("files", {})

    entry = phase3_files.get(file_id)
    if not entry:
        available = list(phase3_files.keys())
        raise RuntimeError(f"No chunks found for '{file_id}'. Available keys: {available}")

    chunks = entry.get("chunk_paths", [])
    if not chunks:
        raise RuntimeError(f"Phase 3 entry for '{file_id}' contains no chunk_paths.")

    return file_id, chunks


def _find_phase_file_entry(data: Dict[str, Any], phase_key: str, file_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Locate a phase entry for a given file_id."""
    files = data.get(phase_key, {}).get("files", {}) or {}
    return file_id, files.get(file_id)


def get_phase4_output_dir(phase_dir: Path, pipeline_json: Path, file_id: str) -> Path:
    """Resolve the output directory for Phase 4 audio."""
    default_path = (phase_dir / "audio_chunks" / file_id).resolve()
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        data = state.read()
        _, entry = _find_phase_file_entry(data, "phase4", file_id)
        audio_dir = entry.get("audio_dir") if entry else None
        if audio_dir:
            path = Path(audio_dir)
            return path if path.is_absolute() else (phase_dir / path).resolve()
        # No audio_dir in entry - use default
        logger.debug("Phase 4 audio_dir not set for %s, using default: %s", file_id, default_path)
    except Exception as exc:
        logger.info(
            "Could not read Phase 4 audio_dir from pipeline.json for %s, using default path: %s",
            file_id, exc
        )
    return default_path


def cleanup_partial_outputs(file_id: str, chunk_id: Optional[str], phase_dir: Path, pipeline_json: Path) -> None:
    """Remove partial/corrupt audio for a specific chunk and clear its pipeline entry.

    Only removes files that are empty or corrupt - preserves valid audio files.
    """
    output_dir = get_phase4_output_dir(phase_dir, pipeline_json, file_id)
    patterns = [f"{chunk_id}*"] if chunk_id else ["chunk_*"]
    for pattern in patterns:
        for candidate in output_dir.glob(pattern):
            try:
                # Only delete if file is empty or corrupt
                if candidate.stat().st_size == 0:
                    candidate.unlink()
                    logger.info(
                        "Removing empty output for chunk %s before retry.",
                        chunk_id or candidate.name,
                    )
                elif candidate.suffix.lower() in (".wav", ".mp3", ".flac"):
                    # Try to validate audio file - only delete if corrupt
                    try:
                        import soundfile as sf
                        info = sf.info(candidate)
                        if info.frames <= 0 or info.duration <= 0:
                            candidate.unlink()
                            logger.info(
                                "Removing corrupt audio for chunk %s before retry.",
                                chunk_id or candidate.name,
                            )
                        else:
                            logger.info(
                                "Preserving valid audio for chunk %s (%.1fs, %d frames).",
                                chunk_id or candidate.name,
                                info.duration,
                                info.frames,
                            )
                    except Exception:
                        # Can't validate - assume corrupt and remove
                        candidate.unlink()
                        logger.info(
                            "Removing unreadable audio for chunk %s before retry.",
                            chunk_id or candidate.name,
                        )
            except Exception as exc:
                logger.warning("Could not process partial output %s: %s", candidate, exc)

    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        with state.transaction() as txn:
            file_key, entry = _find_phase_file_entry(txn.data, "phase4", file_id)
            if entry and chunk_id and chunk_id in entry:
                entry.pop(chunk_id, None)
                logger.debug(
                    "Cleared pipeline entry for chunk %s under file %s",
                    chunk_id,
                    file_key,
                )
    except Exception as exc:
        logger.warning("Failed to clean pipeline entry for chunk %s: %s", chunk_id, exc)


def should_reuse_phase4(
    file_id: str,
    pipeline_json: Path,
    phase_dir: Path,
    expected_engine: str,
    chunk_hash: Optional[str],
    config: OrchestratorConfig,
) -> bool:
    """Determine whether Phase 4 results can be reused."""
    if not config.phase4_reuse_enabled:
        return False

    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        data = state.read()
    except Exception as exc:
        logger.warning("Could not read pipeline.json for reuse check: %s", exc)
        return False

    _, entry = _find_phase_file_entry(data, "phase4", file_id)
    if not entry:
        return False

    audio_paths = entry.get("chunk_audio_paths") or []
    total_chunks = entry.get("total_chunks") or entry.get("metrics", {}).get("total_chunks") or len(audio_paths)
    if total_chunks and len(audio_paths) < total_chunks:
        logger.info(
            "Phase 4 reuse rejected: missing chunks (%d/%d).",
            len(audio_paths),
            total_chunks,
        )
        return False

    if expected_engine:
        engines = set(entry.get("engines_used") or [])
        selected = entry.get("selected_engine")
        if selected:
            engines.add(selected)
        if expected_engine not in engines:
            logger.info(
                "Phase 4 reuse rejected: engine mismatch (%s not in %s).",
                expected_engine,
                engines,
            )
            return False

    if config.min_mos_for_reuse:
        mos = entry.get("metrics", {}).get("avg_mos")
        if mos is not None and mos < config.min_mos_for_reuse:
            logger.info(
                "Phase 4 reuse rejected: MOS %.2f below threshold %.2f",
                mos,
                config.min_mos_for_reuse,
            )
            return False

    if chunk_hash and entry.get("input_hash") and entry.get("input_hash") != chunk_hash:
        logger.info("Phase 4 reuse rejected: chunk text hash changed.")
        return False

    # Validate artifact presence
    output_dir = get_phase4_output_dir(phase_dir, pipeline_json, file_id)
    for path_str in audio_paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = (output_dir / path).resolve()
        if not path.exists() or path.stat().st_size == 0:
            logger.info("Phase 4 reuse rejected: missing or empty file %s", path)
            return False

    logger.info("Phase 4 output will be reused (no changes detected).")
    return True


def record_phase4_metadata(
    file_id: str,
    pipeline_json: Path,
    chunk_hash: Optional[str],
) -> None:
    """Augment phase4 metadata with reuse-friendly fields."""
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        with state.transaction() as txn:
            phase4 = txn.data.get("phase4", {}) or {}
            files = phase4.get("files", {}) or {}
            file_key, entry = _find_phase_file_entry(txn.data, "phase4", file_id)
            entry = entry or {}
            # Derive chunk durations
            durations = []
            for key, value in entry.items():
                if isinstance(value, dict) and value.get("audio_seconds") is not None:
                    durations.append(value.get("audio_seconds"))
            avg_duration = float(sum(durations) / len(durations)) if durations else None
            if chunk_hash:
                entry["input_hash"] = chunk_hash
            entry["chunks_processed"] = entry.get("chunks_completed") or entry.get("total_chunks")
            entry["avg_chunk_duration_sec"] = avg_duration
            if entry.get("duration_seconds") is not None:
                entry["total_tts_time_sec"] = entry["duration_seconds"]
            entry["engine_used"] = entry.get("selected_engine") or entry.get("requested_engine")
            files[file_key] = entry
            phase4["files"] = files
            txn.data["phase4"] = phase4
    except Exception as exc:
        logger.warning("Could not record Phase 4 metadata: %s", exc)


def run_phase_with_retry(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    *,
    state: PipelineState,
    max_retries: int = 2,
    voice_id: Optional[str] = None,
    pipeline_mode: str = "commercial",
    tts_engine: Optional[str] = None,
    policy_engine: Optional[PolicyEngine] = None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
    resume_enabled: bool = True,
) -> bool:
    """
    Run a phase with retry logic.

    Args:
        phase_num: Phase number (1-5, or optional 7/8 stubs)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        max_retries: Maximum retry attempts (default 2)
        voice_id: Optional voice ID for Phase 4 TTS
        pipeline_mode: Pipeline mode (commercial or personal)
        tts_engine: Optional TTS engine override (xtts or kokoro)

    Returns:
        True if successful, False otherwise
    """
    phase_label = f"phase{phase_num}"
    # Track current engine/voice for policy-based switching
    current_engine = tts_engine
    current_voice = voice_id

    if phase_num == 7:
        return run_phase_autonomy_stub(file_id, pipeline_json, state)
    if phase_num == 8:
        return run_phase_reasoning_stub(file_id, pipeline_json, state)

    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.info(f"Retry attempt {attempt}/{max_retries} for Phase {phase_num}")
            retry_ctx = _build_policy_context(
                phase_label,
                file_id,
                pipeline_json,
                status="retry",
                event="phase_retry",
                state=state,
                extra={"attempt": attempt},
            )
            _policy_call(policy_engine, "record_retry", retry_ctx)

            # Apply policy recommendations on retry for Phase 4
            if phase_num == 4 and policy_engine:
                advice = policy_engine.advise({"phase": phase_label, "file_id": file_id})
                cfg = get_orchestrator_config()
                learning_mode = cfg.policy_engine.get("learning_mode", "observe")

                if learning_mode in ("enforce", "tune"):
                    # Auto-switch engine if recommended
                    engine_rec = advice.get("engine", {})
                    if engine_rec.get("action") == "switch_engine":
                        new_engine = engine_rec.get("recommended_engine")
                        if new_engine and new_engine != current_engine:
                            logger.info(f"🤖 PolicyEngine: Auto-switching engine {current_engine} → {new_engine}")
                            current_engine = new_engine

                    # Auto-switch voice if recommended (switch to secondary)
                    voice_rec = advice.get("voice_variant", {})
                    if voice_rec.get("action") == "switch_voice_variant":
                        # Switch to secondary engine as voice change proxy
                        secondary = cfg.tts_engines.secondary
                        if secondary and secondary != current_engine:
                            logger.info(f"🤖 PolicyEngine: Auto-switching to secondary engine {secondary} (voice variant)")
                            current_engine = secondary

            time.sleep(2)  # Brief pause before retry
            if phase_num == 4:
                phase_dir = find_phase_dir(4)
                if phase_dir:
                    cleanup_partial_outputs(file_id, None, phase_dir, pipeline_json)

        success = run_phase(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            current_voice,
            pipeline_mode,
            current_engine,  # Use policy-adjusted engine
            state=state,
            runtime_overrides=runtime_overrides,
            policy_engine=policy_engine,
            resume_enabled=resume_enabled,
        )

        if success:
            return True

    logger.error(f"Phase {phase_num} failed after {max_retries + 1} attempts")

    # Analyze failure with AI if available
    _analyze_failure_with_llm(phase_num, file_id)

    return False


def run_phase(
    phase_num: int,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    pipeline_mode: str = "commercial",
    tts_engine: Optional[str] = None,
    *,
    state: PipelineState,
    runtime_overrides: Optional[Dict[str, Any]] = None,
    policy_engine: Optional[PolicyEngine] = None,
    resume_enabled: bool = True,
) -> bool:
    """
    Run a single phase.

    Args:
        phase_num: Phase number (1-5)
        file_path: Input file path
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        voice_id: Optional voice ID for Phase 4 TTS
        pipeline_mode: Pipeline mode (commercial or personal)
        tts_engine: Optional TTS engine override (xtts or kokoro)

    Returns:
        True if successful, False otherwise
    """
    config = get_orchestrator_config()
    # Determine engine early (needed for Phase 3 routing)
    engine = tts_engine if tts_engine else (config.tts_engines.primary or get_tts_engine())

    phase_overrides = (runtime_overrides or {}).get(f"phase{phase_num}", {})

    # Special handling for Phase 3 (route to Phase 3b for XTTS)
    if phase_num == 3:
        variant = "xtts" if engine == "xtts" else None
        phase_dir = find_phase_dir(phase_num, variant=variant)
        if not phase_dir:
            return False

        logger.info(f"Phase 3: Using chunking variant for {engine}: {phase_dir}")
        return run_phase_standard(
            phase_num,
            phase_dir,
            file_path,
            file_id,
            pipeline_json,
            state,
            phase_overrides=phase_overrides,
            policy_engine=policy_engine,
            voice_id=voice_id,
        )

    # Standard phase directory lookup
    phase_dir = find_phase_dir(phase_num)
    if not phase_dir:
        return False

    logger.info(f"Phase {phase_num} directory: {phase_dir}")

    # Special handling for Phase 4 (Multi-Engine TTS)
    if phase_num == 4:
        logger.info(f"Phase 4: Using TTS engine: {engine}")
        resolved_id, chunk_paths = load_phase3_chunks(file_id, pipeline_json)
        chunk_hash = compute_chunk_text_hash(chunk_paths)
        if should_reuse_phase4(resolved_id, pipeline_json, phase_dir, engine, chunk_hash, config):
            RUN_SUMMARY["phase4_reused"] = True
            return True
        RUN_SUMMARY["phase4_reused"] = False
        # Route to appropriate Phase 4 implementation
        if engine not in {"xtts", "kokoro"}:
            logger.error(f"Unknown TTS engine: {engine}")
            return False

        # Use unified multi-engine system
        return run_phase4_multi_engine(
            phase_dir,
            resolved_id,
            pipeline_json,
            voice_id,
            engine,
            pipeline_mode,
            config=config,
            chunk_hash=chunk_hash,
            resume_enabled=resume_enabled,
        )

    if phase_num == 5 and config.strict_chunk_integrity:
        phase4_dir = find_phase_dir(4)
        if not phase4_dir:
            logger.error("Cannot verify chunk integrity: Phase 4 directory missing.")
            return False
        if not verify_phase4_chunk_integrity(file_id, pipeline_json, phase4_dir):
            RUN_SUMMARY["chunk_integrity_passed"] = False
            return False
        RUN_SUMMARY["chunk_integrity_passed"] = True

    # Standard phases (1, 2, 5) use Poetry
    return run_phase_standard(
        phase_num,
        phase_dir,
        file_path,
        file_id,
        pipeline_json,
        state,
        phase_overrides=phase_overrides,
        policy_engine=policy_engine,
    )


def run_phase_standard(
    phase_num: int,
    phase_dir: Path,
    file_path: Path,
    file_id: str,
    pipeline_json: Path,
    state: PipelineState,
    phase_overrides: Optional[Dict[str, Any]] = None,
    policy_engine: Optional[PolicyEngine] = None,
    voice_id: Optional[str] = None,
) -> bool:
    """Run a standard phase using Poetry."""

    # Fast-path reuse for Phase 2: if extraction already exists with matching hash, skip.
    if phase_num == 2 and should_skip_phase2(file_path, file_id, state):
        return True
    # Fast-path reuse for Phase 3: if chunks already exist with matching text hash, skip.
    if phase_num == 3 and should_skip_phase3(file_id, state):
        return True

    custom_phase3_config: Optional[Path] = None
    if phase_num == 3 and phase_overrides:
        chunk_override = phase_overrides.get("chunk_size")
        if chunk_override and policy_engine:
            custom_phase3_config = _prepare_phase3_config_override(phase_dir, chunk_override, policy_engine.run_id)

    # Special-case Phase 3b (xtts chunking): standalone script, no Poetry env
    if phase_dir.name == "phase3b-xtts-chunking":
        main_script = phase_dir / "sentence_splitter.py"
        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False
        cmd = [
            sys.executable,
            str(main_script),
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
            "--config=config.yaml",
        ]
        logger.info(f"Command: {' '.join(cmd)}")
        start_time = time.perf_counter()
        phase3b_timeout = 18000  # 5 hours for Phase 3b sentence splitting
        try:
            result = subprocess.run(
                cmd,
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=phase3b_timeout,
            )
            duration = time.perf_counter() - start_time
            if result.returncode != 0:
                logger.error(f"Phase {phase_num} FAILED (exit {result.returncode}) in {duration:.1f}s")
                logger.error(f"Error: {result.stderr[-500:]}")
                _store_phase_error(result.stderr)
                return False
            logger.info(f"Phase {phase_num} SUCCESS in {duration:.1f}s")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Phase {phase_num} TIMEOUT ({phase3b_timeout}s)")
            _store_phase_error(f"Phase {phase_num} timeout after {phase3b_timeout} seconds")
            return False
        except Exception as e:
            logger.error(f"Phase {phase_num} ERROR: {e}")
            _store_phase_error(str(e))
            return False

    # Check for venv and install if needed
    venv_dir = phase_dir / ".venv"
    if not venv_dir.exists():
        logger.info(f"Installing dependencies for Phase {phase_num}...")
        try:
            # Configure Poetry to use in-project venv
            subprocess.run(
                [
                    "poetry",
                    "config",
                    "virtualenvs.in-project",
                    "true",
                    "--local",
                ],
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=10,
            )

            # Install dependencies
            result = subprocess.run(
                ["poetry", "install", "--no-root"],
                cwd=str(phase_dir),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"Poetry install failed: {result.stderr}")
                logger.error(f"Poetry stdout: {result.stdout}")
                return False
            logger.info("Dependencies installed successfully")
        except subprocess.TimeoutExpired:
            logger.error("Poetry install timeout (300s)")
            return False
        except Exception as e:
            logger.error(f"Poetry install error: {e}")
            return False
    else:
        logger.info(f"Phase {phase_num} venv already exists")

    # Special handling for Phase 5 (needs config.yaml update)
    if phase_num == 5:
        concat_hint = os.environ.get("PHASE5_CONCAT_ONLY") == "1"
        processed_dir = phase_dir / "processed"
        existing_wavs = list(processed_dir.glob("enhanced_*.wav"))
        if concat_hint and existing_wavs:
            logger.info(
                "Phase 5: concat-only hint set, detected %d enhanced WAVs. Building MP3...",
                len(existing_wavs),
            )
            if concat_phase5_from_existing(phase_dir, file_id, pipeline_json):
                archive_final_audiobook(file_id, pipeline_json)
                return True
            logger.warning("Phase 5: concat-only failed; falling back to full run.")
        elif existing_wavs and len(existing_wavs) >= 100:
            logger.info(
                "Phase 5: detected %d enhanced WAVs, attempting concat-only.",
                len(existing_wavs),
            )
            if concat_phase5_from_existing(phase_dir, file_id, pipeline_json):
                archive_final_audiobook(file_id, pipeline_json)
                return True
            logger.warning("Phase 5: concat-only failed; falling back to full run.")
        return run_phase5_with_config_update(phase_dir, file_id, pipeline_json)

    # Build command with direct script path
    # Special handling for Phase 3b (lightweight script)
    if phase_dir.name == "phase3b-xtts-chunking":
        main_script = phase_dir / "sentence_splitter.py"
        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False
        # Phase 3b is standalone Python (no Poetry)
        cmd = [sys.executable, str(main_script)]
    else:
        # Standard phases use Poetry
        module_dirs = {
            1: "phase1_validation",
            2: "phase2_extraction",
            3: "phase3_chunking",
        }

        module_dir = module_dirs.get(phase_num)

        script_names = {1: "validation.py", 2: "ingest.py", 3: "main.py"}
        script_name = script_names.get(phase_num, "main.py")
        main_script = phase_dir / "src" / module_dir / script_name

        if not main_script.exists():
            logger.error(f"Script not found: {main_script}")
            return False

        # Use relative path from phase directory (critical for Poetry venv resolution)
        entry_points = {
            1: "phase1_validation.validation",
            2: "phase2_extraction.ingest",
            3: "phase3_chunking.main",
        }
        module_entry = entry_points.get(phase_num)
        if module_entry:
            cmd = ["poetry", "run", "python", "-m", module_entry]
        else:
            script_relative = main_script.relative_to(phase_dir)
            cmd = ["poetry", "run", "python", str(script_relative)]

    # Add phase-specific arguments
    if phase_num == 1:
        cmd.extend([f"--file={file_path}", f"--json_path={pipeline_json}"])
    elif phase_num == 2:
        cmd.extend(
            [
                f"--file={file_path}",
                f"--file_id={file_id}",
                f"--json_path={pipeline_json}",
            ]
        )
    elif phase_num == 3:
        config_path = custom_phase3_config or (phase_dir / "config.yaml")
        cmd.extend(
            [
                f"--file_id={file_id}",
                f"--json_path={pipeline_json}",
                f"--config={config_path}",
            ]
        )
        # BUGFIX: Pass voice selection to Phase 3 so chunk voice_overrides are set correctly
        if voice_id:
            cmd.append(f"--voice={voice_id}")

    logger.info(f"Command: {' '.join(cmd)}")

    # Execute
    start_time = time.perf_counter()
    try:
        env = get_clean_env_for_poetry()
        phase_src = phase_dir / "src"
        py_paths = []
        if phase_src.exists():
            py_paths.append(str(phase_src))
        py_paths.append(str(PROJECT_ROOT))
        existing_py_path = env.get("PYTHONPATH")
        if existing_py_path:
            py_paths.append(existing_py_path)
        env["PYTHONPATH"] = os.pathsep.join(py_paths)
        phase_timeout = 18000  # 5 hours for phases 2/3
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            env=env,  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=phase_timeout,
        )

        duration = time.perf_counter() - start_time

        if result.returncode != 0:
            logger.error(f"Phase {phase_num} FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-500:]}")  # Last 500 chars
            _store_phase_error(result.stderr)
            return False

        logger.info(f"Phase {phase_num} SUCCESS in {duration:.1f}s")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Phase {phase_num} TIMEOUT ({phase_timeout}s)")
        _store_phase_error(f"Phase {phase_num} timeout after {phase_timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Phase {phase_num} ERROR: {e}")
        _store_phase_error(str(e))
        return False


def run_phase4_multi_engine(
    phase_dir: Path,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    engine: str = "xtts",
    pipeline_mode: str = "commercial",
    config: Optional[OrchestratorConfig] = None,
    chunk_hash: Optional[str] = None,
    resume_enabled: bool = True,
) -> bool:
    """
    Run Phase 4 with multi-engine support (XTTS v2 primary, Kokoro fallback).

    A per-chunk fallback path will retry failed chunks on the secondary engine
    without reprocessing the entire book.
    """
    logger.info(f"Phase 4 directory: {phase_dir}")
    cfg = config or get_orchestrator_config()
    secondary_engine = cfg.tts_engines.secondary
    workers = max(1, min(cfg.max_tts_workers, os.cpu_count() or cfg.max_tts_workers))
    RUN_SUMMARY["tts_workers_used"] = workers

    def build_base_cmd(
        engine_name: str,
        chunk_index: Optional[int] = None,
        disable_fallback: bool = False,
    ) -> List[str]:
        runner = [sys.executable]
        env_name = os.environ.get("PHASE4_CONDA_ENV") or os.environ.get("CONDA_DEFAULT_ENV")
        if cfg.prefer_shell_tts_execution and env_name:
            runner = ["conda", "run", "-n", env_name, "python"]
        elif cfg.prefer_shell_tts_execution:
            runner = ["python"]

        cmd = [
            *runner,
            str(phase_dir / "engine_runner.py"),
            f"--engine={engine_name}",
            f"--file_id={file_id}",
            f"--json_path={pipeline_json}",
            f"--workers={workers}",
        ]
        if voice_id:
            cmd.append(f"--voice={voice_id}")
        cmd.append("--config=config.yaml")
        if disable_fallback:
            cmd.append("--disable_fallback")
        if chunk_index is not None:
            cmd.append(f"--chunk_id={chunk_index}")
        # Only enable resume if not doing a fresh run
        if resume_enabled:
            cmd.append("--resume")
        return cmd

    def collect_failed_chunks() -> List[str]:
        """Check Phase 4 completion by examining chunk_audio_paths, not individual chunk keys.

        Phase 4 writes a file-level entry with chunk_audio_paths[] containing successful outputs.
        It does NOT write individual chunk_0001, chunk_0002 keys to pipeline.json.

        Returns:
            List of chunk IDs that failed (empty if all succeeded or if phase4 entry is missing)
        """
        try:
            state = PipelineState(pipeline_json, validate_on_read=False)
            data = state.read()
            _, entry = _find_phase_file_entry(data, "phase4", file_id)
            if not entry:
                return []

            # Check the actual contract: Phase 4 should record a file-level
            # `chunk_audio_paths` array listing successful outputs. For older
            # or mixed-format pipeline.json files this key may be absent; in
            # that case persist a one-line fallback for compatibility so
            # downstream logic can rely on the canonical key.
            chunk_audio_paths = entry.get("chunk_audio_paths")
            if chunk_audio_paths is None:
                try:
                    # Persist an explicit empty list to ease backward-compatibility
                    state = PipelineState(pipeline_json, validate_on_read=False)
                    with state.transaction() as txn:
                        phase4 = txn.data.get("phase4", {}) or {}
                        files = phase4.get("files", {}) or {}
                        files.setdefault(file_id, {})
                        files[file_id].setdefault("chunk_audio_paths", [])
                        phase4["files"] = files
                        txn.data["phase4"] = phase4
                    chunk_audio_paths = []
                except Exception:
                    chunk_audio_paths = []

            # Get expected chunks from Phase 3, the source of truth
            _, p3_entry = _find_phase_file_entry(data, "phase3", file_id)
            if p3_entry and p3_entry.get("chunk_paths"):
                expected_chunks = len(p3_entry.get("chunk_paths"))
            else:
                # Fallback to phase 4 entry if phase 3 is missing
                expected_chunks = (
                    entry.get("total_chunks")
                    or entry.get("chunks_processed")
                    or entry.get("metrics", {}).get("total_chunks", 0)
                ) or 0

            # If we have chunk_audio_paths, verify they all exist (resolve relative paths)
            if chunk_audio_paths:
                missing = []
                output_dir = get_phase4_output_dir(phase_dir, pipeline_json, file_id)
                for path in chunk_audio_paths:
                    p = Path(path)
                    if not p.is_absolute():
                        p = (output_dir / p).resolve()
                    if not p.exists() or p.stat().st_size == 0:
                        chunk_id = Path(path).stem
                        missing.append(chunk_id)
                # Return list of missing chunk ids (empty list => none missing)
                return missing

            # If chunk_audio_paths is empty, scan output directory for existing audio files
            output_dir = get_phase4_output_dir(phase_dir, pipeline_json, file_id)
            if output_dir.exists():
                existing_chunks = set()
                for audio_file in output_dir.glob("chunk_*.wav"):
                    if audio_file.stat().st_size > 0:
                        existing_chunks.add(audio_file.stem)
                        logger.debug("Found existing audio: %s", audio_file.stem)

                if existing_chunks:
                    # Only mark chunks as failed if they don't exist on disk
                    if expected_chunks > 0:
                        expected_ids = {f"chunk_{i:04d}" for i in range(1, int(expected_chunks) + 1)}
                        missing = list(expected_ids - existing_chunks)
                        if missing:
                            logger.info("Found %d existing audio files, %d missing", len(existing_chunks), len(missing))
                        return sorted(missing)
                    else:
                        # No expected count but we have files - assume success
                        logger.info("Found %d audio files on disk (no expected count)", len(existing_chunks))
                        return []

                # If chunk_audio_paths is empty and no files on disk, consider all expected chunks as failed
                if expected_chunks > 0:
                    return [f"chunk_{i:04d}" for i in range(1, int(expected_chunks) + 1)]
            
        except Exception as exc:
            logger.warning(
                "Unable to inspect pipeline.json for failed chunks (file_id=%s): %s",
                file_id, exc, exc_info=True
            )
            # Return empty list but log at WARNING level so this is visible
            # The caller should check logs if Phase 4 claims success but audio is missing
            return []

    def run_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
        start_time = time.perf_counter()
        env = os.environ.copy()
        phase_src = phase_dir / "src"
        py_paths = []
        if phase_src.exists():
            py_paths.append(str(phase_src))
        py_paths.append(str(PROJECT_ROOT))
        existing_py = env.get("PYTHONPATH")
        if existing_py:
            py_paths.append(existing_py)
        env["PYTHONPATH"] = os.pathsep.join(py_paths)
        phase4_timeout = cfg.get_phase_timeout(4)

        # Stream output to console in real-time so we can see "Skipping chunk_XXXX" logs
        logger.info("Phase 4 command: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            cwd=str(Path(phase_dir).resolve()),
            env=env,
            capture_output=False,  # Don't capture - let it stream to console
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=phase4_timeout,
        )
        duration = time.perf_counter() - start_time
        if result.returncode != 0:
            logger.error(
                "Phase 4 command failed (exit %s) in %.1fs",
                result.returncode,
                duration,
            )
        else:
            logger.info("Phase 4 command finished in %.1fs", duration)
        return result

    # Clear stale Phase 4 state before fresh run to prevent retry logic
    # from attempting to process chunks from previous runs with different chunking
    if not resume_enabled:
        try:
            state = PipelineState(pipeline_json, validate_on_read=False)
            with state.transaction() as txn:
                phase4 = txn.data.get("phase4", {}) or {}
                files = phase4.get("files", {}) or {}
                if file_id in files:
                    # Clear chunk_audio_paths to prevent stale data from old runs
                    files[file_id]["chunk_audio_paths"] = []
                    logger.info("Cleared stale Phase 4 chunk_audio_paths for fresh run")
                phase4["files"] = files
                txn.data["phase4"] = phase4
        except Exception as exc:
            logger.warning(f"Failed to clear Phase 4 state: {exc}")

    # Primary engine run - disable fallback so we can drive per-chunk retries ourselves.
    primary_cmd = build_base_cmd(
        engine,
        disable_fallback=bool(cfg.per_chunk_fallback and secondary_engine),
    )
    result = run_cmd(primary_cmd)

    failed_chunks = collect_failed_chunks()
    # Ensure `success` is always defined. If primary command exited cleanly
    # and no failed chunks reported, consider this a success by default.
    success = (result.returncode == 0 and not failed_chunks)
    if failed_chunks and cfg.per_chunk_fallback and secondary_engine:
        RUN_SUMMARY["per_chunk_fallback_used"] = True
        logger.info(
            "Retrying %d failed chunks via %s",
            len(failed_chunks),
            secondary_engine,
        )
        for chunk_id in failed_chunks:
            match = re.search(r"(\d+)", chunk_id)
            if not match:
                logger.warning("Cannot parse chunk id %s for fallback", chunk_id)
                continue
            cleanup_partial_outputs(file_id, chunk_id, phase_dir, pipeline_json)
            chunk_index = int(match.group(1))
            fallback_cmd = build_base_cmd(secondary_engine, chunk_index=chunk_index)
            run_cmd(fallback_cmd)
        # Re-read failures after fallback attempts
        failed_chunks = collect_failed_chunks()

        # Determine expected total and available successes
        try:
            state = PipelineState(pipeline_json, validate_on_read=False)
            data = state.read()
            _, entry = _find_phase_file_entry(data, "phase4", file_id)
            chunk_audio_paths = (entry or {}).get("chunk_audio_paths") or []
            expected_total = (
                (entry or {}).get("total_chunks")
                or (entry or {}).get("chunks_processed")
                or (entry or {}).get("metrics", {}).get("total_chunks")
                or 0
            )
        except Exception as exc:
            logger.error(
                "Failed to re-read pipeline state after fallback attempts (file_id=%s): %s",
                file_id, exc, exc_info=True
            )
            chunk_audio_paths = []
            expected_total = 0
            # State is unreadable - don't claim success, let collect_failed_chunks determine

        # Success criteria:
        # - At least one chunk_audio_paths entry exists, and
        # - If an expected_total is recorded, the number of paths >= expected_total, and
        # - No missing chunks reported by collect_failed_chunks()
        success = (
            bool(chunk_audio_paths)
            and (int(expected_total) == 0 or len(chunk_audio_paths) >= int(expected_total))
            and not failed_chunks
        )

        # Respect a clean zero-exit status as success even if pipeline.json lacked totals
        if result.returncode == 0 and not failed_chunks:
            success = True
    if success:
        logger.info("Phase 4 SUCCESS with %s", engine)
        record_phase4_metadata(file_id, pipeline_json, chunk_hash)
        return True

    logger.error("Phase 4 failed; remaining failed chunks: %s", failed_chunks)
    # Record failures to ErrorRegistry for tracking and future self-repair
    if failed_chunks:
        _record_chunk_failures(file_id, failed_chunks, engine, "TTS synthesis exhausted all fallbacks")

        # Attempt self-repair strategies via DeadChunkRepair
        repair = _get_dead_chunk_repair()
        if repair:
            logger.info("🔧 Attempting DeadChunkRepair strategies for %d failed chunks...", len(failed_chunks))
            # Note: Full repair requires engine_manager integration; for now we just register the failures
            # and log that repair was attempted. The next run can use the registry to try different strategies.
            for chunk_id in failed_chunks:
                registry = _get_error_registry()
                if registry:
                    # Add a repair attempt marker
                    from self_repair.repair_loop import RepairAttempt
                    attempt = RepairAttempt(
                        strategy="orchestrator_fallback_exhausted",
                        success=False,
                        chunk_id=chunk_id,
                        error="Primary and secondary engines both failed",
                    )
                    registry.add_attempt(chunk_id, attempt)
            logger.info("🔧 Failures logged to ErrorRegistry for future analysis")

    return False


def verify_phase4_chunk_integrity(file_id: str, pipeline_json: Path, phase4_dir: Path) -> bool:
    """Ensure all expected chunk audio files exist before concatenation."""
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        data = state.read()
    except Exception as exc:
        logger.error("Cannot read pipeline.json for integrity check: %s", exc)
        return False

    resolved_id, entry = _find_phase_file_entry(data, "phase4", file_id)
    if not entry:
        logger.error("No Phase 4 entry found for %s; cannot concatenate.", file_id)
        return False

    chunk_audio_paths = entry.get("chunk_audio_paths") or []
    if not chunk_audio_paths:
        for key, value in entry.items():
            if isinstance(value, dict) and value.get("audio_path"):
                chunk_audio_paths.append(value["audio_path"])
    expected_total = entry.get("total_chunks") or len(chunk_audio_paths)
    if expected_total and len(chunk_audio_paths) < expected_total:
        logger.error(
            "Chunk integrity failed: only %d of %d audio chunks recorded for %s.",
            len(chunk_audio_paths),
            expected_total,
            resolved_id,
        )
        return False

    output_dir = get_phase4_output_dir(phase4_dir, pipeline_json, resolved_id)
    missing_paths: List[str] = []
    zero_paths: List[str] = []
    for path_str in chunk_audio_paths:
        path = Path(path_str)
        if not path.is_absolute():
            path = (output_dir / path).resolve()
        if not path.exists():
            missing_paths.append(str(path))
        elif path.stat().st_size == 0:
            zero_paths.append(str(path))

    failed_chunks = [key for key, value in entry.items() if isinstance(value, dict) and value.get("status") == "failed"]
    if failed_chunks:
        logger.error(
            "Chunk integrity failed: %d failed chunks remain: %s",
            len(failed_chunks),
            failed_chunks,
        )
        return False

    if missing_paths or zero_paths:
        if missing_paths:
            logger.error(
                "Chunk integrity failed: missing files:\n%s",
                "\n".join(missing_paths),
            )
        if zero_paths:
            logger.error(
                "Chunk integrity failed: zero-byte files:\n%s",
                "\n".join(zero_paths),
            )
        return False

    logger.info("Phase 4 chunk integrity check passed for %s", resolved_id)
    return True


def mark_phase_skipped(pipeline_json: Path, phase_num: int) -> None:
    """Mark a phase as skipped due to global budget exhaustion."""
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        with state.transaction() as txn:
            phase_key = f"phase{phase_num}"
            entry = txn.data.get(phase_key) or {}
            if not isinstance(entry, dict):
                entry = {}
            entry.setdefault("status", "failed")
            errors = entry.get("errors") or []
            errors.append("Global time budget exceeded")
            entry["errors"] = errors
            entry["skipped"] = True
            txn.data[phase_key] = entry
    except Exception as exc:
        logger.warning("Unable to mark Phase %s as skipped: %s", phase_num, exc)


def _get_optional_phase_status(state: PipelineState, phase_key: str, file_id: str) -> str:
    """Return status for optional phases (phaseG/phaseH), defaulting to 'pending'."""
    snapshot = read_state_snapshot(state, warn=False)
    phase_data = snapshot.get(phase_key, {}) if isinstance(snapshot, dict) else {}
    files = phase_data.get("files", {}) if isinstance(phase_data, dict) else {}
    if isinstance(files, dict) and file_id in files:
        return str(files[file_id].get("status", "pending"))
    return "pending"


def _record_optional_phase_status(
    state: PipelineState,
    phase_key: str,
    file_id: str,
    status: str,
    note: Optional[str] = None,
) -> None:
    """Persist status for optional phases without impacting core execution."""
    try:
        with state.transaction() as txn:
            phase_block, file_entry = ensure_phase_and_file(txn.data, phase_key, file_id)
            file_entry["status"] = status
            now = datetime.utcnow().isoformat() + "Z"
            ts = file_entry.get("timestamps") or {}
            ts.setdefault("start", now)
            ts["end"] = now
            file_entry["timestamps"] = ts
            if note:
                file_entry["notes"] = note
            phase_block.setdefault("files", {})[file_id] = file_entry
    except Exception as exc:
        logger.debug("Optional phase %s status not recorded: %s", phase_key, exc)


def run_phase_autonomy_stub(file_id: str, pipeline_json: Path, state: PipelineState) -> bool:
    """
    Phase G (Autonomy) stub.

    Skips unless pipeline.json marks phaseG status as "ready". When ready,
    records a success marker without performing any work.
    """
    status = _get_optional_phase_status(state, "phaseG", file_id)
    if status != "ready":
        logger.info("Phase G (Autonomy) status '%s'; skipping stub execution.", status)
        return True

    logger.info("Phase G (Autonomy) ready; running stub (no-op).")
    _record_optional_phase_status(
        state,
        "phaseG",
        file_id,
        "success",
        note="Autonomy scaffolding stub executed (no-op).",
    )
    return True


def run_phase_reasoning_stub(file_id: str, pipeline_json: Path, state: PipelineState) -> bool:
    """
    Phase H (Reasoning) stub.

    Skips unless pipeline.json marks phaseH status as "ready". When ready,
    records a success marker without performing any work.
    """
    status = _get_optional_phase_status(state, "phaseH", file_id)
    if status != "ready":
        logger.info("Phase H (Reasoning) status '%s'; skipping stub execution.", status)
        return True

    logger.info("Phase H (Reasoning) ready; running stub (no-op).")
    _record_optional_phase_status(
        state,
        "phaseH",
        file_id,
        "success",
        note="Reasoning scaffolding stub executed (no-op).",
    )
    return True


def run_postrun_self_repair(
    pipeline_json: Path,
    file_id: str,
    autonomy_cfg: AutonomyConfig,
    self_repair_cfg: SelfRepairConfig,
) -> None:
    """Optional self-repair stage after pipeline completion (opt-in)."""
    if not autonomy_cfg.enable_self_repair:
        logger.info("Self-repair disabled; skipping post-run RepairLoop.")
        return

    try:
        from self_repair.log_parser import LogParser
        from self_repair.repair_loop import RepairLoop, DeadChunkRepair
        from self_repair.patch_staging import PatchStaging
    except Exception as exc:
        logger.warning("Self-repair dependencies unavailable: %s", exc)
        return

    logs_dir = Path(".pipeline") / "policy_logs"
    if not logs_dir.exists():
        logger.info("Self-repair: no policy_logs directory found; skipping.")
        return

    log_files = sorted(
        [p for p in logs_dir.glob("*.log") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not log_files:
        logger.info("Self-repair: no log files found; skipping.")
        return

    latest_log = log_files[0]
    logger.info("Self-repair: analyzing log %s", latest_log)

    log_parser = LogParser()
    dead_chunk_repair = _get_dead_chunk_repair(
        enable_text_rewrite=self_repair_cfg.enable_text_rewrite,
        rewrite_conf_threshold=self_repair_cfg.rewrite_confidence_threshold,
        memory_enabled=autonomy_cfg.memory_enabled,
    ) or DeadChunkRepair(
        enable_text_rewrite=self_repair_cfg.enable_text_rewrite,
        rewrite_confidence_threshold=self_repair_cfg.rewrite_confidence_threshold,
        memory_enabled=autonomy_cfg.memory_enabled,
    )
    reasoner = _get_llama_reasoner() if autonomy_cfg.use_reasoner else None
    stager = PatchStaging()

    try:
        events = log_parser.parse_file(latest_log, max_lines=1000)
    except Exception as exc:
        logger.warning("Self-repair: failed to parse log %s: %s", latest_log, exc)
        return

    try:
        repair_loop = RepairLoop(
            log_parser=log_parser,
            dead_chunk_repair=dead_chunk_repair,
            staging_dir=stager.staging_dir,
        )
        suggestions = repair_loop.analyze_and_suggest(events, reasoner=reasoner)
        stager.stage_suggestions(suggestions, source="orchestrator")
        logger.info("Self-repair: suggestions staged (if any).")
    except Exception as exc:
        logger.warning("Self-repair: RepairLoop failed: %s", exc)


def run_reasoning_evaluator(
    pipeline_json: Path,
    file_id: str,
    reasoning_cfg: ReasoningConfig,
) -> None:
    """Optional post-run evaluator (opt-in, non-destructive)."""
    if not reasoning_cfg.enable_evaluator:
        return

    try:
        from phaseH_reasoning.evaluator import ReasoningEvaluator
    except Exception as exc:
        logger.warning("Reasoning evaluator unavailable: %s", exc)
        return

    try:
        evaluator = ReasoningEvaluator()
        summary = evaluator.evaluate_run(
            pipeline_json=pipeline_json,
            file_id=file_id,
        )
        runtime_dir = Path(".pipeline") / "policy_runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        summary_path = runtime_dir / "last_run_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2))
        logger.info("Reasoning evaluator summary written to %s", summary_path)
    except Exception as exc:
        logger.warning("Reasoning evaluator failed: %s", exc)
        return None


def run_reasoning_diagnostics(
    reasoning_cfg: ReasoningConfig,
    autonomy_cfg: AutonomyConfig,
) -> None:
    """Optional diagnostics using Llama (opt-in, non-destructive)."""
    if not reasoning_cfg.enable_diagnostics:
        return

    try:
        from agents.llama_diagnostics import LlamaDiagnostics
        from autonomy.memory_store import summarize_history, add_experience
    except Exception as exc:
        logger.warning("Diagnostics dependencies unavailable: %s", exc)
        return

    summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
    if not summary_path.exists():
        logger.info("Diagnostics skipped: no evaluator summary found.")
        return

    try:
        evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Diagnostics skipped: cannot read evaluator summary: %s", exc)
        return

    benchmarks = load_latest_benchmark()
    try:
        from policy_engine.policy_engine import get_benchmark_history

        history = get_benchmark_history(limit=3)
        if history:
            benchmarks = history[0] if isinstance(history, list) else benchmarks
    except Exception:
        pass
    memory_summary = summarize_history()

    agent = LlamaDiagnostics()
    try:
        diagnostics = agent.analyze_runs(
            evaluator_summary=evaluator_summary or {},
            memory_summary=memory_summary or {},
            benchmarks=benchmarks or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Diagnostics agent failed: %s", exc)
        return

    diag_dir = Path(".pipeline") / "diagnostics"
    diag_dir.mkdir(parents=True, exist_ok=True)
    diag_path = diag_dir / f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        diag_path.write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
        logger.info("Diagnostics written to %s", diag_path)
        if autonomy_cfg.memory_enabled and add_experience:
            add_experience("diagnostics", diagnostics)
    except Exception as exc:
        logger.warning("Failed to write diagnostics: %s", exc)


def run_autonomy_planner(
    autonomy_cfg: AutonomyConfig,
    pipeline_json: Path,
    genre_cfg: GenreConfig,
    autonomy_mode: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Optional planner to emit recommendations (no auto-apply)."""
    if autonomy_cfg.planner_mode == "disabled":
        return

    try:
        from phaseG_autonomy.planner import AutonomyPlanner
    except Exception as exc:
        logger.warning("Autonomy planner unavailable: %s", exc)
        return

    try:
        planner = AutonomyPlanner(
            mode=autonomy_cfg.planner_mode,
            policy_kernel_enabled=autonomy_cfg.policy_kernel_enabled,
            autonomy_mode=autonomy_mode,
        )
        payload = planner.recommend(
            pipeline_json=pipeline_json,
            genre_config=genre_cfg,
            experiments_cfg=orchestrator_config.experiments,
            autonomy_cfg=autonomy_cfg,
            autonomy_mode=autonomy_mode,
        )
        if payload.get("status") != "disabled":
            logger.info("Autonomy planner generated recommendations in %s mode", autonomy_cfg.planner_mode)
        return payload
    except Exception as exc:
        logger.warning("Autonomy planner failed: %s", exc)
        return None


def load_latest_staged_recommendation() -> Optional[Dict[str, Any]]:
    """Load the most recent staged recommendation, if any."""
    staged_dir = Path(".pipeline") / "staged_recommendations"
    if not staged_dir.exists():
        return None
    candidates = sorted(staged_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def load_latest_benchmark() -> Optional[Dict[str, Any]]:
    """Load the latest benchmark report if available."""
    history_dir = Path(".pipeline") / "benchmark_history"
    if not history_dir.exists():
        return None
    candidates = sorted(history_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def _reset_experiment_state() -> None:
    """Remove temporary experiment-related attributes to prevent leakage."""
    global _ACTIVE_EXPERIMENT, _TEMP_EXPERIMENT_OVERRIDES, _EXPERIMENT_CONTEXT, _CURRENT_EXPERIMENT
    _ACTIVE_EXPERIMENT = None
    _CURRENT_EXPERIMENT = None
    _TEMP_EXPERIMENT_OVERRIDES = {}
    _EXPERIMENT_CONTEXT = {}


def _reset_supervised_overrides() -> None:
    """Clear supervised override state after each run."""
    global _SUPERVISED_OVERRIDES, _AUTONOMOUS_OVERRIDES
    _SUPERVISED_OVERRIDES = {}
    _AUTONOMOUS_OVERRIDES = {}


def _apply_experiments_if_enabled(
    orchestrator_config: OrchestratorConfig,
    runtime_overrides: Dict[str, Any],
    file_id: str,
) -> Dict[str, Any]:
    """
    Apply in-memory experiment overrides based on staged recommendations.

    Experiments are opt-in and never persist to configs.
    """
    experiments_cfg = orchestrator_config.experiments
    if not experiments_cfg.enable:
        return runtime_overrides

    recommendation = load_latest_staged_recommendation()
    if not recommendation:
        return runtime_overrides

    experiments = recommendation.get("experiments") or []
    if not experiments:
        return runtime_overrides

    applied = []
    global _ACTIVE_EXPERIMENT, _TEMP_EXPERIMENT_OVERRIDES, _EXPERIMENT_CONTEXT, _CURRENT_EXPERIMENT
    for exp in experiments:
        if len(applied) >= experiments_cfg.limit_per_run:
            break
        if not isinstance(exp, str):
            continue
        if exp.startswith("chunk") and "chunk_size" in experiments_cfg.allowed:
            runtime_overrides["experiment_chunk_size"] = exp
            applied.append(exp)
        elif "engine" in exp and "engine_preference" in experiments_cfg.allowed:
            runtime_overrides["experiment_engine_pref"] = exp
            applied.append(exp)
        elif "rewrite" in exp and "rewrite_policy" in experiments_cfg.allowed:
            runtime_overrides["experiment_rewrite_policy"] = exp
            applied.append(exp)

    if applied:
        experiments_dir = Path(".pipeline") / "experiments"
        experiments_dir.mkdir(parents=True, exist_ok=True)
        exp_record = {
            "file_id": file_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "applied": applied,
            "dry_run": experiments_cfg.dry_run,
            "runtime_overrides": runtime_overrides,
        }
        exp_path = experiments_dir / f"{file_id}_experiments.json"
        exp_path.write_text(json.dumps(exp_record, indent=2), encoding="utf-8")

        if orchestrator_config.autonomy.memory_enabled:
            try:
                from autonomy.memory_store import add_experience

                add_experience("experiment", exp_record)
            except Exception:
                pass

        _ACTIVE_EXPERIMENT = applied[:]
        _CURRENT_EXPERIMENT = applied[:]
        _TEMP_EXPERIMENT_OVERRIDES = dict(runtime_overrides) if not experiments_cfg.dry_run else {}
        _EXPERIMENT_CONTEXT = {"file_id": file_id, "dry_run": experiments_cfg.dry_run}

    # Respect dry-run: do not apply overrides to runtime if dry_run is true
    if experiments_cfg.dry_run:
        return runtime_overrides
    return _TEMP_EXPERIMENT_OVERRIDES or runtime_overrides


def _apply_supervised_overrides(
    orchestrator_config: OrchestratorConfig,
    runtime_overrides: Dict[str, Any],
    file_id: str,
    recommendation: Optional[Dict[str, Any]] = None,
    safety_ctx: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply temporary in-memory overrides when autonomy.mode == supervised
    and planner confidence meets threshold. Never persists changes.
    """
    if orchestrator_config.autonomy.mode != "supervised":
        return runtime_overrides

    rec = recommendation or load_latest_staged_recommendation()
    if not rec:
        return runtime_overrides

    if safety_ctx and not safety_ctx.get("allow_overrides", True):
        _log_decision_event(
            "supervised",
            {},
            safety_ctx,
            run_id,
            source="runtime_supervised",
            allowed=False,
        )
        return runtime_overrides

    confidence = float(rec.get("confidence", 0.0))
    if confidence < orchestrator_config.autonomy.supervised_threshold:
        return runtime_overrides

    suggested = (safety_ctx or {}).get("filtered_overrides") or rec.get("suggested_changes") or {}
    if not suggested:
        _log_decision_event(
            "supervised",
            {},
            safety_ctx,
            run_id,
            source="runtime_supervised",
            allowed=False,
        )
        return runtime_overrides

    overrides = dict(runtime_overrides)

    global _SUPERVISED_OVERRIDES

    if "phase3.chunk_size" in suggested:
        overrides.setdefault("phase3", {})
        overrides["phase3"]["chunk_size_hint"] = suggested["phase3.chunk_size"]

    if "phase4.engine_preference" in suggested:
        overrides.setdefault("phase4", {})
        overrides["phase4"]["engine"] = suggested["phase4.engine_preference"].get("preferred")

    if "rewrite_policy" in suggested:
        overrides.setdefault("phase4", {})
        overrides["phase4"]["rewrite_policy"] = suggested["rewrite_policy"]

    _SUPERVISED_OVERRIDES = {
        "overrides": overrides,
        "confidence": confidence,
        "source": "supervised_mode",
    }
    _log_decision_event(
        "supervised",
        overrides,
        safety_ctx,
        run_id,
        source="runtime_supervised",
        allowed=True,
    )

    # Record supervised application to memory if enabled
    if orchestrator_config.autonomy.memory_enabled:
        try:
            from autonomy.memory_store import add_experience

            add_experience(
                "planner_action",
                {
                    "mode": "supervised",
                    "file_id": file_id,
                    "applied": True,
                    "suggested_changes": suggested,
                    "confidence": confidence,
                },
            )
        except Exception:
            pass

    return overrides


def _apply_autonomous_overrides(
    orchestrator_config: OrchestratorConfig,
    runtime_overrides: Dict[str, Any],
    file_id: str,
    autonomy_mode: Optional[str] = None,
    recommendation: Optional[Dict[str, Any]] = None,
    safety_ctx: Optional[Dict[str, Any]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply temporary in-memory overrides when autonomy.mode == autonomous.
    Overrides are filtered by policy and budget and never persist.
    """
    mode = autonomy_mode or orchestrator_config.autonomy.mode
    if mode != "autonomous":
        return runtime_overrides

    rec = recommendation or load_latest_staged_recommendation()
    if not rec:
        return runtime_overrides

    if safety_ctx and (not safety_ctx.get("allow_overrides", True) or safety_ctx.get("autonomy_mode") != "autonomous"):
        _log_decision_event(
            "autonomous",
            {},
            safety_ctx,
            run_id,
            source="runtime_autonomous",
            allowed=False,
        )
        return runtime_overrides

    autonomous_rec = rec.get("autonomous_recommendations") or {}
    changes = (safety_ctx or {}).get("filtered_overrides") or autonomous_rec.get("changes") or rec.get("suggested_changes") or {}
    confidence = float(autonomous_rec.get("confidence", rec.get("confidence", 0.0) or 0.0))
    if not changes:
        _log_decision_event(
            "autonomous",
            {},
            safety_ctx,
            run_id,
            source="runtime_autonomous",
            allowed=False,
        )
        return runtime_overrides

    safe_changes = dict(changes)
    if not safe_changes:
        _log_decision_event(
            "autonomous",
            {},
            safety_ctx,
            run_id,
            source="runtime_autonomous",
            allowed=False,
        )
        return runtime_overrides

    overrides = dict(runtime_overrides)
    if "phase3.chunk_size" in safe_changes:
        overrides.setdefault("phase3", {})["chunk_size_hint"] = safe_changes["phase3.chunk_size"]
    if "phase4.engine_preference" in safe_changes:
        pref_payload = safe_changes["phase4.engine_preference"]
        if isinstance(pref_payload, dict):
            overrides.setdefault("phase4", {})["engine"] = pref_payload
    if "rewrite_policy" in safe_changes:
        overrides.setdefault("phase4", {})["rewrite_policy"] = safe_changes["rewrite_policy"]

    global _AUTONOMOUS_OVERRIDES
    _AUTONOMOUS_OVERRIDES = {
        "overrides": overrides,
        "confidence": confidence,
        "source": "autonomous_mode",
    }
    _log_decision_event(
        "autonomous",
        overrides,
        safety_ctx,
        run_id,
        source="runtime_autonomous",
        allowed=True,
    )

    if orchestrator_config.autonomy.memory_enabled:
        try:
            from autonomy.memory_store import add_experience

            add_experience(
                "planner_action",
                {
                    "mode": "autonomous",
                    "file_id": file_id,
                    "applied": bool(safe_changes),
                    "suggested_changes": safe_changes,
                    "confidence": confidence,
                },
            )
        except Exception:
            pass

    return overrides


def run_postrun_repair_pipeline(
    pipeline_json: Path,
    file_id: str,
    self_repair_cfg: SelfRepairConfig,
) -> None:
    """
    Parse logs and run RepairLoop after a run (opt-in, non-destructive).
    """
    if not (self_repair_cfg.enable_log_parser or self_repair_cfg.enable_repair_loop):
        return

    try:
        from self_repair.log_parser import LogParser
        from self_repair.repair_loop import RepairLoop, DeadChunkRepair
    except Exception as exc:
        logger.warning("RepairLoop dependencies unavailable: %s", exc)
        return

    logs_dir = Path(".pipeline") / "policy_logs"
    parser = LogParser()
    events = []
    if self_repair_cfg.enable_log_parser:
        events = parser.parse_logs(logs_dir, max_files=3, max_lines=1000)

    if not (events and self_repair_cfg.enable_repair_loop):
        return

    dead_chunk_repair = DeadChunkRepair()
    repair_loop = RepairLoop(log_parser=parser, dead_chunk_repair=dead_chunk_repair)
    repairs = repair_loop.run(
        events,
        confidence_threshold=self_repair_cfg.repair_confidence_threshold,
    )

    if not repairs:
        return

    run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    repairs_dir = Path(".pipeline") / "repairs" / run_id
    repairs_dir.mkdir(parents=True, exist_ok=True)

    successful_repairs = []
    for item in repairs:
        result = item.get("result") or {}
        audio = result.get("audio")
        if audio is None:
            continue
        confidence = float(item.get("confidence", 0.0))
        chunk_id = item.get("chunk_id") or "unknown_chunk"
        try:
            import soundfile as sf

            out_path = repairs_dir / f"{chunk_id}.wav"
            sf.write(out_path, audio, result.get("sample_rate", 24000))
            logger.info(
                "Repaired chunk %s written to %s (non-destructive, conf=%.2f).",
                chunk_id,
                out_path,
                confidence,
            )
            successful_repairs.append(
                {"chunk": chunk_id, "path": str(out_path), "confidence": confidence}
            )
        except Exception as exc:
            logger.warning("Failed to write repaired audio for %s: %s", chunk_id, exc)
    return successful_repairs


def run_phase5_with_config_update(phase_dir: Path, file_id: str, pipeline_json: Path) -> bool:
    """
    Run Phase 5 with config.yaml update.

    Phase 5 reads pipeline.json path from config.yaml, not command-line args.
    """
    # Ensure Poetry uses local venv and install dependencies
    logger.info("Configuring Phase 5 environment...")

    # Step 1: Configure Poetry to use in-project venv
    try:
        subprocess.run(
            ["poetry", "config", "virtualenvs.in-project", "true", "--local"],
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as e:
        logger.warning(f"Could not configure Poetry (non-fatal): {e}")

    # Step 2: Ensure dependencies are installed (idempotent - fast if already installed)
    venv_dir = phase_dir / ".venv"
    if venv_dir.exists():
        logger.info("Phase 5 venv detected; skipping Poetry dependency install.")
    else:
        logger.info("Verifying Phase 5 dependencies...")
        try:
            result = subprocess.run(
                ["poetry", "install", "--no-root"],
                cwd=str(phase_dir),
                env=get_clean_env_for_poetry(),  # Use clean environment for Poetry
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error(f"Poetry install failed (exit {result.returncode})")
                if result.stdout:
                    logger.error(f"STDOUT: {result.stdout}")
                if result.stderr:
                    logger.error(f"STDERR: {result.stderr}")
                return False
            logger.info("Dependencies verified/installed successfully")
        except Exception as e:
            logger.error(f"Poetry install error: {e}")
            return False

    config_path = phase_dir / "src" / "phase5_enhancement" / "config.yaml"

    # Read existing config
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to read Phase 5 config.yaml: {e}")
        return False

    # Update pipeline_json path (make it absolute)
    config["pipeline_json"] = str(pipeline_json)

    # Phase 5 looks for audio in input_dir (which should point to Phase 4 output)
    # Default is "../phase4_tts/audio_chunks" which should work from phase5_enhancement
    if PHASE4_AUDIO_DIR:
        config["input_dir"] = str(PHASE4_AUDIO_DIR)
    elif "input_dir" not in config:
        config["input_dir"] = "../phase4_tts/audio_chunks"

    # Set quality settings to prevent chunk exclusion
    # Disable quality validation so all chunks are included
    config["quality_validation_enabled"] = False
    config["snr_threshold"] = 10.0
    config["noise_reduction_factor"] = 0.1

    # Allow resume by default; only wipe state if explicitly requested
    if "resume_on_failure" not in config:
        config["resume_on_failure"] = True
    logger.info("Resume_on_failure=%s", config.get("resume_on_failure"))

    clear_phase5 = os.environ.get("PHASE5_CLEAR", "0") == "1"
    if clear_phase5:
        try:
            state = PipelineState(pipeline_json, validate_on_read=False)
            with state.transaction() as txn:
                if "phase5" in txn.data:
                    old_chunk_count = len(txn.data.get("phase5", {}).get("chunks", []))
                    logger.info(f"WARNING: Clearing {old_chunk_count} old Phase 5 chunks from pipeline.json")
                    del txn.data["phase5"]
            logger.info("✓ Cleared Phase 5 data from pipeline.json")
        except Exception as e:
            logger.warning(f"Could not clear Phase 5 data (non-fatal): {e}")

        import shutil

        processed_dir = phase_dir / "processed"
        output_dir = phase_dir / "output"
        try:
            if processed_dir.exists():
                file_count = len(list(processed_dir.glob("*.wav")))
                if file_count > 0:
                    logger.info(f"WARNING: Clearing {file_count} old files from processed/ directory")
                    shutil.rmtree(processed_dir)
                    processed_dir.mkdir(parents=True, exist_ok=True)
                    logger.info("OK Cleared processed/ directory")

            if output_dir.exists():
                audiobook_path = output_dir / "audiobook.mp3"
                if audiobook_path.exists():
                    logger.info("WARNING: Removing old audiobook.mp3")
                    audiobook_path.unlink()
                    logger.info("OK Removed old audiobook.mp3")
        except Exception as e:
            logger.warning(f"Could not clear processed files (non-fatal): {e}")

    # Always refresh audiobook title so metadata matches current input
    config["audiobook_title"] = humanize_title(file_id)

    # Write updated config
    try:
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Updated Phase 5 config with pipeline_json: {pipeline_json}")
    except Exception as e:
        logger.error(f"Failed to update Phase 5 config.yaml: {e}")
        return False

    # Build command - Phase 5 only accepts --config, --chunk_id, --skip_concatenation
    # Run as module (not script) because main.py uses relative imports
    cmd = [
        "poetry",
        "run",
        "python",
        "-m",
        "phase5_enhancement.main",
        "--config=config.yaml",
    ]

    logger.info(f"Command: {' '.join(cmd)}")

    # Execute
    phase5_timeout = 1800  # 30 minutes for Phase 5 enhancement
    start_time = time.perf_counter()
    try:
        env = get_clean_env_for_poetry()
        src_path = phase_dir / "src"
        if src_path.exists():
            existing_py_path = env.get("PYTHONPATH", "")
            py_paths = [str(src_path), str(PROJECT_ROOT)]
            if existing_py_path:
                py_paths.append(existing_py_path)
            env["PYTHONPATH"] = os.pathsep.join(py_paths)
            logger.info(f"Phase 5 PYTHONPATH override: {env['PYTHONPATH']}")

        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            env=env,  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=phase5_timeout,
        )

        duration = time.perf_counter() - start_time

        if result.returncode != 0:
            logger.error(f"Phase 5 FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-1000:]}")
            _store_phase_error(result.stderr)
            return False

        logger.info(f"Phase 5 SUCCESS in {duration:.1f}s")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Phase 5 TIMEOUT ({phase5_timeout}s)")
        _store_phase_error(f"Phase 5 timeout after {phase5_timeout} seconds")
        return False
    except Exception as e:
        logger.error(f"Phase 5 ERROR: {e}")
        _store_phase_error(str(e))
        return False


def _timestamp_to_seconds(timestamp: str, separator: str = ",") -> float:
    """Convert SRT/VTT timestamp to seconds."""
    hms, ms = timestamp.split(separator)
    hours, minutes, seconds = hms.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds) + int(ms) / (1000 if separator == "," else 1000)


def _seconds_to_timestamp(seconds: float, separator: str = ",") -> str:
    millis = int(round(seconds * 1000))
    hours, remainder = divmod(millis, 3600 * 1000)
    minutes, remainder = divmod(remainder, 60 * 1000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{separator}{millis:03d}"


def rescale_subtitle_file(path: Path, audio_duration: float, separator: str = ",") -> bool:
    """Stretch subtitle timestamps linearly to match the target audio duration."""
    if not path.exists() or audio_duration <= 0:
        return False
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    new_lines: List[str] = []
    last_end = 0.0
    timestamp_pattern = re.compile(
        r"(\\d\\d:\\d\\d:\\d\\d[\\,\\.]\\d\\d\\d)\\s+-->\\s+(\\d\\d:\\d\\d:\\d\\d[\\,\\.]\\d\\d\\d)"
    )
    for line in lines:
        match = timestamp_pattern.search(line)
        if match:
            start = _timestamp_to_seconds(match.group(1), separator=separator)
            end = _timestamp_to_seconds(match.group(2), separator=separator)
            last_end = max(last_end, end)
    if last_end <= 0:
        return False
    scale = audio_duration / last_end
    for line in lines:
        match = timestamp_pattern.search(line)
        if match:
            start = _timestamp_to_seconds(match.group(1), separator=separator) * scale
            end = _timestamp_to_seconds(match.group(2), separator=separator) * scale
            start_ts = _seconds_to_timestamp(start, separator=separator)
            end_ts = _seconds_to_timestamp(end, separator=separator)
            line = timestamp_pattern.sub(f"{start_ts} --> {end_ts}", line)
        new_lines.append(line)
    path.write_text("\n".join(new_lines), encoding="utf-8")
    return True


def get_audio_duration_seconds(audio_path: Path) -> Optional[float]:
    """Return audio duration using ffprobe if available."""
    if not audio_path.exists():
        return None
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def maybe_backup_align_subtitles(
    audio_path: Path,
    srt_path: Path,
    vtt_path: Path,
    metrics: Dict[str, Any],
    config: SubtitleConfig,
) -> bool:
    """Apply a simple rescaling alignment if primary alignment quality is low."""
    if not config.enable_backup_align:
        return False

    coverage = metrics.get("coverage") or metrics.get("coverage_ratio")
    drift = metrics.get("drift_seconds") or metrics.get("max_drift")
    if (
        coverage is not None
        and coverage >= config.min_coverage_ratio
        and (drift is None or abs(drift) <= config.max_drift_sec)
    ):
        return False

    audio_duration = get_audio_duration_seconds(audio_path)
    if not audio_duration:
        return False

    success = False
    if srt_path.exists():
        success = rescale_subtitle_file(srt_path, audio_duration, separator=",") or success
    if vtt_path.exists():
        success = rescale_subtitle_file(vtt_path, audio_duration, separator=".") or success
    if success:
        logger.info("Using backup subtitle alignment for %s", audio_path.stem)
    return success


def run_phase5_5_subtitles(
    phase5_dir: Path,
    file_id: str,
    pipeline_json: Path,
    enable_subtitles: bool = False,
) -> bool:
    """
    Phase 5.5: Generate subtitles (optional).

    Args:
        phase5_dir: Path to phase5_enhancement directory
        file_id: File identifier
        pipeline_json: Path to pipeline.json
        enable_subtitles: If False, skip this phase

    Returns:
        True if successful or skipped, False if failed
    """
    if not enable_subtitles:
        logger.info("Phase 5.5 (Subtitles): Skipped (disabled)")
        return True

    logger.info("=== Phase 5.5: Subtitle Generation ===")

    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        pipeline_data = state.read()

        audiobook_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)
        if not audiobook_path.exists():
            logger.error(f"Phase 5.5: Audiobook not found at {audiobook_path}")
            return False

        phase2_data = pipeline_data.get("phase2", {})
        phase2_files = phase2_data.get("files", {}) or {}
        text_file = None
        phase2_entry = phase2_files.get(file_id)
        if phase2_entry:
            text_file = (
                phase2_entry.get("extracted_text_path") or phase2_entry.get("path") or phase2_entry.get("output_file")
            )
        else:
            if not phase2_files:
                logger.warning("Phase 5.5: No phase2.files entries found in pipeline.json")
            else:
                logger.warning(
                    "Phase 5.5: file_id '%s' not found in Phase 2 entries",
                    file_id,
                )

        if not text_file:
            text_file = Path("phase2-extraction") / "extracted_text" / f"{file_id}.txt"
            if not text_file.exists():
                logger.warning(
                    "Phase 5.5: Could not find Phase 2 text path, defaulting to %s",
                    text_file,
                )

        # Build subtitle generation command
        # Run as module (not script) because subtitles.py uses relative imports
        cmd = [
            "poetry",
            "run",
            "python",
            "-m",
            "phase5_enhancement.subtitles",
            "--audio",
            str(audiobook_path),
            "--file-id",
            file_id,
            "--output-dir",
            str(phase5_dir / "subtitles"),
            "--model",
            "small",  # Balance of speed and accuracy
        ]
        cmd.extend(["--pipeline-json", str(pipeline_json)])

        # Add reference text if available for WER calculation
        if text_file and Path(text_file).exists():
            cmd.extend(["--reference-text", str(text_file)])
        else:
            text_file = None  # ensure log clarity

        logger.info(f"Phase 5.5: Resolved audiobook path: {audiobook_path}")
        logger.info(f"Phase 5.5: Resolved reference text: {text_file or 'None (using audio-only workflow)'}")

        logger.info(f"Command: {' '.join(cmd)}")

        # Execute subtitle generation
        phase55_timeout = 3600  # 60 minutes for Phase 5.5 subtitle generation
        start_time = time.perf_counter()
        result = subprocess.run(
            cmd,
            cwd=str(phase5_dir),
            env=get_clean_env_for_poetry(),  # Clean environment for Poetry virtualenv detection
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=phase55_timeout,
        )

        duration = time.perf_counter() - start_time

        if result.returncode != 0:
            logger.error(f"Phase 5.5 FAILED (exit {result.returncode}) in {duration:.1f}s")
            logger.error(f"Error: {result.stderr[-1000:]}")

            try:
                with state.transaction(operation="phase5_5_fail") as txn:
                    phase_block, file_entry = ensure_phase_and_file(txn.data, "phase5_5", file_id)
                    file_entry.update(
                        {
                            "status": "failed",
                            "artifacts": {},
                            "metrics": {},
                            "errors": [result.stderr[-500:]],
                            "timestamps": {
                                "end": time.time(),
                                "duration": duration,
                            },
                        }
                    )
                    phase_block["status"] = "partial"
                    phase_block.setdefault("errors", []).append(
                        {
                            "file": file_id,
                            "message": result.stderr[-200:].strip(),
                            "phase": "phase5_5",
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not update pipeline.json with failure: {e}")

            return False

        # Parse output to get subtitle paths
        srt_path = phase5_dir / "subtitles" / f"{file_id}.srt"
        vtt_path = phase5_dir / "subtitles" / f"{file_id}.vtt"
        metrics_path = phase5_dir / "subtitles" / f"{file_id}_metrics.json"

        # Load metrics if available
        metrics = {}
        if metrics_path.exists():
            with open(metrics_path, "r") as f:
                metrics = json.loads(f.read())

        # Backup alignment if coverage/drift are weak
        backup_used = maybe_backup_align_subtitles(
            audiobook_path,
            srt_path,
            vtt_path,
            metrics,
            get_orchestrator_config().subtitles,
        )
        if backup_used:
            RUN_SUMMARY["backup_subtitles_used"] = True
            metrics["backup_alignment"] = True

        with state.transaction(operation="phase5_5_success") as txn:
            phase_block, file_entry = ensure_phase_and_file(txn.data, "phase5_5", file_id)
            file_entry.update(
                {
                    "status": "success",
                    "artifacts": {
                        "srt_file": str(srt_path),
                        "vtt_file": str(vtt_path),
                    },
                    "metrics": metrics,
                    "errors": [],
                    "timestamps": {
                        "end": time.time(),
                        "duration": duration,
                    },
                }
            )
            phase_block["status"] = "success"

        logger.info(f"Phase 5.5 SUCCESS in {duration:.1f}s")
        logger.info(f"SRT: {srt_path}")
        logger.info(f"VTT: {vtt_path}")
        if metrics.get("coverage"):
            logger.info(f"Coverage: {metrics['coverage']:.2%}")
        if metrics.get("wer") is not None:
            logger.info(f"WER: {metrics['wer']:.2%}")

        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Phase 5.5 TIMEOUT ({phase55_timeout}s)")
        return False
    except Exception as e:
        logger.error(f"Phase 5.5 ERROR: {e}", exc_info=True)
        return False


def process_single_chunk(
    phase_dir: Path,
    conda_env: str,
    main_script: str,
    ref_file: str,
    chunk_id: int,
    file_id: str,
    pipeline_json: Path,
    voice_id: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
) -> bool:
    """Process a single TTS chunk with optional voice override."""
    cmd = [
        "conda",
        "run",
        "-n",
        conda_env,
        "--no-capture-output",
        "python",
        main_script,
        f"--chunk_id={chunk_id}",
        f"--file_id={file_id}",
        f"--json_path={pipeline_json}",
        "--config=config.yaml",  # Phase 4 expects --config, not --enable-splitting
    ]

    if extra_args:
        cmd.extend(extra_args)

    # Add voice override if specified
    if voice_id:
        cmd.append(f"--voice_id={voice_id}")

    # Set UTF-8 encoding for subprocess (critical for Unicode text)
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            cmd,
            cwd=str(phase_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=None,  # 20 minutes per chunk
            env=env,  # Pass environment with UTF-8 encoding
        )

        if result.returncode != 0:
            error_log = phase_dir / f"chunk_{chunk_id}_error.log"
            with open(error_log, "w", encoding="utf-8", errors="replace") as f:
                f.write(result.stderr)
                f.write("\n\nSTDOUT:\n")
                f.write(result.stdout)
            logger.warning(f"Chunk {chunk_id} failed (logged to {error_log})")
            return False

        return True

    except subprocess.TimeoutExpired:
        logger.warning(f"Chunk {chunk_id} timeout (20min)")
        return False
    except Exception as e:
        logger.warning(f"Chunk {chunk_id} error: {e}")
        return False


def summarize_results(pipeline_json: Path):
    """Create summary table of pipeline results."""
    try:
        state = PipelineState(pipeline_json, validate_on_read=False)
        data = state.read()
    except Exception as exc:
        logger.debug("summarize_results: pipeline state read failed: %s", exc)
        return

    if not RICH_AVAILABLE:
        return

    table = Table(title="Pipeline Results")
    table.add_column("Phase", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")

    for i in range(1, 6):
        phase_key = f"phase{i}"
        phase_data = data.get(phase_key, {})
        status = phase_data.get("status", "pending")

        # Get details
        details = ""
        if phase_key == "phase3":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                chunk_count = len(fdata.get("chunk_paths", []))
                details = f"{chunk_count} chunks"
                break
        elif phase_key == "phase4":
            files = phase_data.get("files", {})
            for fid, fdata in files.items():
                audio_count = len(fdata.get("chunk_audio_paths", []))
                avg_mos = fdata.get("metrics", {}).get("avg_mos", 0)
                details = f"{audio_count} audio chunks, MOS={avg_mos:.2f}"
                break

        # Color-code status
        if status == "success":
            status_display = f"[green]{status}[/green]"
        elif status == "failed":
            status_display = f"[red]{status}[/red]"
        else:
            status_display = f"[yellow]{status}[/yellow]"

        table.add_row(f"Phase {i}", status_display, details)

    console.print(table)


def _run_lexicon_updater() -> None:
    """Placeholder for lexicon update logic."""
    logger.info("Lexicon updater hook called (no-op).")


def run_pipeline(
    file_path: Path,
    voice_id: Optional[str] = None,
    tts_engine: str = "chatterbox",
    mastering_preset: Optional[str] = None,
    phases: List[int] = None,
    pipeline_json: Optional[Path] = None,
    enable_subtitles: bool = False,
    max_retries: int = 3,
    no_resume: bool = False,
    progress_callback=None,
    concat_only: bool = False,
    auto_mode: bool = False,
    policy_engine: Optional[PolicyEngine] = None,
    enable_llama_chunker: bool = True,
    enable_llama_rewriter: bool = True,
    cancel_event: Optional[Any] = None,
) -> Dict:
    """
    Programmatic interface to run the audiobook pipeline.

    Args:
        file_path: Path to input book file (EPUB, PDF, etc.)
        voice_id: Voice ID to use for TTS (ignored if auto_mode=True)
        tts_engine: TTS engine to use ("chatterbox", "f5", "xtts")
        mastering_preset: Audio mastering preset name
        phases: List of phases to run (default: [1,2,3,4,5])
        pipeline_json: Path to pipeline.json (default: PROJECT_ROOT/pipeline.json)
        enable_subtitles: Whether to generate subtitles (Phase 5.5)
        max_retries: Max retries per phase
        no_resume: Disable resume from checkpoint (run all phases fresh)
        progress_callback: Optional callback(phase_num, percentage, message)
        concat_only: Reuse existing enhanced WAVs in Phase 5 (skip re-enhancement)
        auto_mode: Let AI select voice based on genre detection (overrides voice_id)
        enable_llama_chunker: Enable LlamaChunker for semantic chunking in Phase 3
        enable_llama_rewriter: Enable LlamaRewriter for ASR-based text fixes in Phase 4

    Returns:
        Dict with:
            - success: bool
            - audiobook_path: Path to final audiobook
            - metadata: Dict of pipeline metadata
            - error: Optional error message
    """
    # Resolve paths
    file_path = Path(file_path).resolve()
    if not file_path.exists():
        return {
            "success": False,
            "error": f"File not found: {file_path}",
            "audiobook_path": None,
            "metadata": {},
        }

    file_id = file_path.stem

    if pipeline_json is None:
        pipeline_json = PROJECT_ROOT / "pipeline.json"
    else:
        pipeline_json = Path(pipeline_json).resolve()

    orchestrator_config = get_orchestrator_config()

    # Initialize Ollama/LLM for AI-powered features (LlamaChunker, LlamaReasoner, etc.)
    # This checks: ollama package installed, server running, model available
    # Non-blocking - pipeline continues even if Ollama unavailable
    llm_config = getattr(orchestrator_config, "llm", None) or {}
    if llm_config.get("enable", True):
        llm_model = llm_config.get("model", "llama3.1:8b-instruct-q4_K_M")
        ollama_status = ensure_ollama_ready(model=llm_model)
        if ollama_status["available"]:
            logger.info(f"🤖 LLM features enabled: {ollama_status['model']}")
        else:
            logger.warning(f"🤖 LLM features disabled: {ollama_status['message']}")
    else:
        logger.info("🤖 LLM features disabled in config")

    # Set environment variables for LLM features (inherited by subprocesses)
    # These allow UI to control LlamaChunker and LlamaRewriter per-run
    if not enable_llama_chunker:
        os.environ["DISABLE_LLAMA_CHUNKER"] = "1"
        logger.info("🤖 LlamaChunker disabled by UI setting")
    elif "DISABLE_LLAMA_CHUNKER" in os.environ:
        del os.environ["DISABLE_LLAMA_CHUNKER"]

    if not enable_llama_rewriter:
        os.environ["DISABLE_LLAMA_REWRITER"] = "1"
        logger.info("🤖 LlamaRewriter disabled by UI setting")
    elif "DISABLE_LLAMA_REWRITER" in os.environ:
        del os.environ["DISABLE_LLAMA_REWRITER"]

    if policy_engine is None:
        policy_config = orchestrator_config.policy_engine or {}
        policy_engine = PolicyEngine(
            logging_enabled=bool(policy_config.get("logging", False)),
            learning_mode=str(policy_config.get("learning_mode", "observe")),
            autonomy_mode=orchestrator_config.autonomy.mode,
        )

    if policy_engine:
        policy_engine.start_new_run()
        runtime_overrides = policy_engine.prepare_run_overrides(file_id=file_id)
    else:
        runtime_overrides = {}
    current_run_id = getattr(policy_engine, "run_id", None) if policy_engine else None
    if not current_run_id:
        current_run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    try:
        if orchestrator_config.autonomy.enable_experiments:
            orchestrator_config.experiments.enable = True
    except Exception:
        pass

    staged_recommendation = load_latest_staged_recommendation()

    # Memory feedback (opt-in)
    if orchestrator_config.autonomy.enable_memory_feedback:
        try:
            from autonomy import memory_store

            runtime_overrides.setdefault("run_context", {})
            runtime_overrides["run_context"]["memory_recent"] = memory_store.load_recent_events()
            runtime_overrides["run_context"]["run_history"] = memory_store.load_recent_runs()
        except Exception:
            pass

    base_autonomy_mode = orchestrator_config.autonomy.mode
    if orchestrator_config.autonomy.supervised_mode:
        base_autonomy_mode = "supervised"
    if not orchestrator_config.autonomy.enable:
        base_autonomy_mode = "disabled"
    orchestrator_config.autonomy.mode = base_autonomy_mode

    safety_ctx = _evaluate_autonomy_safety(
        orchestrator_config,
        staged_recommendation,
        run_id=current_run_id,
        context="runtime_overrides",
    )
    effective_autonomy_mode = safety_ctx.get("autonomy_mode", base_autonomy_mode) or base_autonomy_mode
    if safety_ctx.get("downgrade_reasons"):
        effective_autonomy_mode = "supervised"

    global_safety = {"allow_autonomy": True, "blocked_reasons": [], "downgrade_to_supervised": False}
    global_cfg = getattr(orchestrator_config.autonomy, "global_settings", {}) or {}
    if global_cfg.get("enable_full_autonomy", False):
        run_summary_input = dict(RUN_SUMMARY)
        if not global_cfg.get("require_passing_self_eval", True):
            run_summary_input.pop("self_eval_passed", None)
        if not global_cfg.get("require_schema_valid", True):
            run_summary_input.pop("schema_valid", None)
        if not global_cfg.get("require_no_high_drift", True):
            run_summary_input.pop("consistency_passed", None)
            run_summary_input.pop("phaseS_consistency", None)
        safety_eval_input = safety_ctx.get("safety_eval", {}) if global_cfg.get("require_safety_envelope", True) else {}
        drift_input = safety_ctx.get("drift", {}) if global_cfg.get("require_no_high_drift", True) else {}
        global_safety = enforce_global_safety(
            run_summary=run_summary_input,
            readiness=safety_ctx.get("readiness", {}),
            safety_envelope=safety_eval_input,
            escalation=safety_ctx.get("escalation", {}),
            drift=drift_input,
            stability=safety_ctx.get("stability", {}),
            budget={"allows": safety_ctx.get("budget_allows", True)},
        )
        if not global_safety.get("allow_autonomy", False):
            staged_recommendation = {}
            effective_autonomy_mode = "supervised"
            safety_ctx["allow_overrides"] = False
            safety_ctx["downgrade_reasons"] = (safety_ctx.get("downgrade_reasons") or []) + global_safety.get("blocked_reasons", [])
            try:
                final_payload = {
                    "run_id": current_run_id,
                    "mode": effective_autonomy_mode,
                    "blocked_reasons": global_safety.get("blocked_reasons", []),
                    "downgrade_to_supervised": True,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                final_path = _timestamped_event_path(Path(".pipeline") / "autonomy" / "final_safety")
                final_path.write_text(json.dumps(final_payload, indent=2), encoding="utf-8")
            except Exception:
                logger.debug("Final safety log write failed", exc_info=True)

    # Apply effective mode in-memory only for this run
    orchestrator_config.autonomy.mode = effective_autonomy_mode

    # Apply opt-in experiments (in-memory only)
    runtime_overrides = _apply_experiments_if_enabled(
        orchestrator_config,
        runtime_overrides,
        file_id,
    )

    # Apply supervised autonomy overrides (in-memory only)
    runtime_overrides = _apply_supervised_overrides(
        orchestrator_config,
        runtime_overrides,
        file_id,
        recommendation=staged_recommendation,
        safety_ctx=safety_ctx,
        run_id=current_run_id,
    )
    # Apply autonomous overrides (in-memory only)
    runtime_overrides = _apply_autonomous_overrides(
        orchestrator_config,
        runtime_overrides,
        file_id,
        autonomy_mode=effective_autonomy_mode,
        recommendation=staged_recommendation,
        safety_ctx=safety_ctx,
        run_id=current_run_id,
    )
    phase4_overrides = runtime_overrides.get("phase4") or {}
    phase_retry_overrides = runtime_overrides.get("retry_policy") or {}
    engine_override = phase4_overrides.get("engine")
    if engine_override:
        preferred_engine = engine_override.get("preferred")
        if preferred_engine:
            if preferred_engine != tts_engine:
                logger.info(
                    "Policy override: forcing Phase 4 engine -> %s",
                    preferred_engine,
                )
            tts_engine = preferred_engine
    voice_override = phase4_overrides.get("voice")
    if voice_override:
        new_voice = voice_override.get("voice_id")
        if new_voice:
            if new_voice != voice_id:
                logger.info("Policy override: forcing voice -> %s", new_voice)
            voice_id = new_voice

    if phases is None:
        phases = orchestrator_config.phases_to_run
    pipeline_mode = orchestrator_config.pipeline_mode.lower()

    RUN_SUMMARY.update(
        {
            "phase4_reused": False,
            "per_chunk_fallback_used": False,
            "tts_workers_used": None,
            "chunk_integrity_passed": None,
            "backup_subtitles_used": False,
            "budget_exceeded": False,
        }
    )

    # Prepare canonical pipeline state access
    try:
        state = PipelineState(pipeline_json, validate_on_read=True)
    except Exception as exc:  # pragma: no cover - fallback path
        logger.warning("Falling back to non-validating pipeline state: %s", exc)
        state = PipelineState(pipeline_json, validate_on_read=False)
    resume_enabled = not no_resume

    # Concat-only hint for Phase 5
    if concat_only:
        os.environ["PHASE5_CONCAT_ONLY"] = "1"
    else:
        os.environ.pop("PHASE5_CONCAT_ONLY", None)

    # Auto mode: Let AI select voice based on genre detection (Phase 3)
    if auto_mode:
        logger.info("🤖 Auto mode enabled: AI will select voice based on detected genre")
        voice_id = None  # Don't pass --voice to Phase 3; let genre detection choose
    elif voice_id:
        logger.info(f"Using manual voice selection: {voice_id}")

        # Auto-detect engine from voice configuration
        try:
            voices_config_path = PROJECT_ROOT / "configs" / "voices.json"
            if voices_config_path.exists():
                import json
                with open(voices_config_path, 'r', encoding='utf-8') as f:
                    voices_data = json.load(f)
                voice_config = voices_data.get("voices", {}).get(voice_id, {})
                voice_engine = voice_config.get("engine")
                if voice_engine and voice_engine != tts_engine:
                    logger.info(f"Auto-detected engine '{voice_engine}' for voice '{voice_id}' (overriding default '{tts_engine}')")
                    tts_engine = voice_engine
        except Exception as e:
            logger.warning(f"Could not auto-detect engine for voice '{voice_id}': {e}")

    # Predictive Failure Analysis
    try:
        from agents.predictive_failure_agent import PredictiveFailureAgent
        predictive_agent = PredictiveFailureAgent(str(pipeline_json), file_id)
        analysis_results = predictive_agent.analyze()
        if analysis_results["warnings"]:
            print_panel(
                "[bold yellow]Predictive Failure Analysis Warnings:[/bold yellow]\n" + "\n".join(f"- {w}" for w in analysis_results["warnings"]),
                "PRE-FLIGHT CHECK",
                "yellow"
            )
        if analysis_results["recommendations"]:
             print_panel(
                "[bold cyan]Predictive Failure Analysis Recommendations:[/bold cyan]\n" + "\n".join(f"- {r}" for r in analysis_results["recommendations"]),
                "PRE-FLIGHT CHECK",
                "cyan"
            )
    except ImportError:
        logger.info("PredictiveFailureAgent not found, skipping analysis.")
    except Exception as e:
        logger.warning(f"Predictive failure analysis failed: {e}")

    # Run phases
    policy_phase_timers: Dict[str, float] = {}
    completed_phases = []

    try:
        # Add Phase 0 (Audiobook Director) if auto_mode is enabled
        if auto_mode and 0 not in phases:
            phases.insert(0, 0)

        # If Phase 0 is included, run it first to generate the Production Bible
        if 0 in phases:
            print_status("Running Phase 0: Audiobook Director...", style="bold cyan")
            progress_callback(0, 0.1, "Analyzing book for Production Bible")
            if not run_phase_0_director(file_id, file_path, pipeline_json):
                logger.error("Phase 0 (Audiobook Director) failed. Cannot proceed in auto_mode.")
                # In auto_mode, the bible is critical, so we stop.
                if auto_mode:
                    return {
                        "success": False,
                        "error": "Failed to generate Production Bible in auto_mode.",
                        "audiobook_path": None,
                    }
            progress_callback(0, 1.0, "Production Bible check complete")

        # Filter out phase 0 so we don't try to run it in the main loop
        phases_to_run = sorted([p for p in phases if p != 0])

        for phase_num in phases_to_run:
            if cancel_event and cancel_event.is_set():
                logger.warning("Pipeline cancelled by user request.")
                break
            # Call progress callback if provided
            if progress_callback:
                progress_callback(phase_num, 0.0, f"Starting Phase {phase_num}...")

            # Check resume status (phase-first view)
            resume_status: Optional[str] = None
            if resume_enabled:
                resume_status = check_phase_status(state, phase_num, file_id)
                if resume_status == "success":
                    logger.info(f"Skipping Phase {phase_num} (already completed)")
                    completed_phases.append(phase_num)
                    if progress_callback:
                        progress_callback(phase_num, 100.0, "Already completed")
                    continue
                elif resume_status in {"failed", "partial"}:
                    logger.info(f"Retrying Phase {phase_num} (previous status: {resume_status})")

            # Run phase with retries
            logger.info(f"Running Phase {phase_num}...")
            phase_label = f"phase{phase_num}"
            policy_phase_timers[phase_label] = time.perf_counter()
            start_ctx = _build_policy_context(
                phase_label,
                file_id,
                pipeline_json,
                status="starting",
                event="phase_start",
                state=state,
                extra={"resume_status": resume_status},
            )
            _policy_call(policy_engine, "record_phase_start", start_ctx)

            phase_retry_config = phase_retry_overrides.get(phase_label, {})
            retry_budget = phase_retry_config.get("suggested_retries", max_retries)
            try:
                retry_budget = int(retry_budget)
            except (TypeError, ValueError):
                retry_budget = max_retries
            if retry_budget != max_retries:
                logger.info(
                    "Policy override: %s retry budget -> %s",
                    phase_label,
                    retry_budget,
                )

            success = run_phase_with_retry(
                phase_num,
                file_path,
                file_id,
                pipeline_json,
                state=state,
                max_retries=retry_budget,
                voice_id=voice_id,
                pipeline_mode=pipeline_mode,
                tts_engine=tts_engine,
                policy_engine=policy_engine,
                runtime_overrides=runtime_overrides,
                resume_enabled=resume_enabled,
            )

            if not success:
                failure_duration = _pop_phase_duration(policy_phase_timers, phase_label)
                failure_ctx = _build_policy_context(
                    phase_label,
                    file_id,
                    pipeline_json,
                    status="failed",
                    event="phase_failure",
                    state=state,
                    duration_ms=failure_duration,
                    include_snapshot=True,
                    errors=[f"Phase {phase_num} failed"],
                )
                _policy_call(policy_engine, "record_failure", failure_ctx)
                _log_policy_advice(policy_engine, failure_ctx, phase_label, file_id)
                if policy_engine:
                    policy_engine.complete_run(
                        success=False,
                        metadata={"file_id": file_id, "failed_phase": phase_label},
                    )
                return {
                    "success": False,
                    "error": f"Pipeline failed at Phase {phase_num}",
                    "audiobook_path": None,
                    "metadata": {},
                }

            logger.info(f"Phase {phase_num} completed successfully")

            if progress_callback:
                progress_callback(phase_num, 100.0, "Complete")

            duration_ms = _pop_phase_duration(policy_phase_timers, phase_label)
            end_ctx = _build_policy_context(
                phase_label,
                file_id,
                pipeline_json,
                status="success",
                event="phase_end",
                state=state,
                duration_ms=duration_ms,
                include_snapshot=True,
            )
            _policy_call(policy_engine, "record_phase_end", end_ctx)
            _log_policy_advice(policy_engine, end_ctx, phase_label, file_id)

            # Archive after Phase 5
            if phase_num == 5:
                archive_final_audiobook(file_id, pipeline_json)

            completed_phases.append(phase_num)

        # Phase 5.5: Subtitles (optional)
        if 5 in completed_phases and enable_subtitles:
            logger.info("Running Phase 5.5 (Subtitles)...")
            phase5_dir = find_phase_dir(5)
            if phase5_dir:
                subtitle_phase_label = "phase5.5"
                policy_phase_timers[subtitle_phase_label] = time.perf_counter()
                subtitle_start_ctx = _build_policy_context(
                    subtitle_phase_label,
                    file_id,
                    pipeline_json,
                    status="starting",
                    event="phase_start",
                    state=state,
                )
                _policy_call(policy_engine, "record_phase_start", subtitle_start_ctx)

                success = run_phase5_5_subtitles(phase5_dir, file_id, pipeline_json, enable_subtitles=True)

                duration_ms = _pop_phase_duration(policy_phase_timers, subtitle_phase_label)
                if success:
                    end_ctx = _build_policy_context(
                        subtitle_phase_label,
                        file_id,
                        pipeline_json,
                        status="success",
                        event="phase_end",
                        state=state,
                        duration_ms=duration_ms,
                        include_snapshot=True,
                    )
                    _policy_call(policy_engine, "record_phase_end", end_ctx)
                    _log_policy_advice(policy_engine, end_ctx, subtitle_phase_label, file_id)
                else:
                    failure_ctx = _build_policy_context(
                        subtitle_phase_label,
                        file_id,
                        pipeline_json,
                        status="failed",
                        event="phase_failure",
                        state=state,
                        duration_ms=duration_ms,
                        include_snapshot=True,
                        errors=["Phase 5.5 (Subtitles) failed"],
                    )
                    _policy_call(policy_engine, "record_failure", failure_ctx)
                    _log_policy_advice(policy_engine, failure_ctx, subtitle_phase_label, file_id)
                    logger.warning("Phase 5.5 (Subtitles) failed - continuing anyway")

        # Find final audiobook path
        audiobook_path = None
        phase5_dir = find_phase_dir(5)
        if phase5_dir:
            audiobook_path = resolve_phase5_audiobook_path(file_id, pipeline_json, phase5_dir)

        # Build per-file metadata view from canonical state
        file_phase_view = build_file_phase_view(state, file_id)

        # Phase M: profile logging (opt-in, additive-only, reporting)
        try:
            auto_cfg = orchestrator_config.autonomy
        except Exception:
            auto_cfg = None

        enable_profile_learning = bool(getattr(auto_cfg, "enable_profile_learning", False)) if auto_cfg else False
        enable_genre_learning = bool(getattr(auto_cfg, "enable_genre_learning", False)) if auto_cfg else False
        enable_profile_fusion = bool(getattr(auto_cfg, "enable_profile_fusion", False)) if auto_cfg else False

        if enable_profile_learning or enable_genre_learning or enable_profile_fusion:
            try:
                from autonomy import memory_store
                from autonomy import profiles as profile_utils
                from autonomy import profile_manager
                from autonomy import reinforcement
            except Exception:
                memory_store = None
                profile_utils = None
                profile_manager = None
                reinforcement = None

            if memory_store and profile_utils:
                run_history = memory_store.load_run_history(limit=100) if hasattr(memory_store, "load_run_history") else []
                metadata_history = (
                    memory_store.load_metadata_history(limit=50) if hasattr(memory_store, "load_metadata_history") else []
                )
                memory_summary = memory_store.summarize_history(max_events=200) if hasattr(memory_store, "summarize_history") else None
                reward_history = (
                    reinforcement.load_reward_history(limit=20) if reinforcement and hasattr(reinforcement, "load_reward_history") else []
                )
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

                stable_profiles: Dict[str, Any] = {}
                genre_profile: Dict[str, Any] = {}

                if enable_profile_learning:
                    stable_profiles = {
                        "engine": profile_utils.compute_engine_stability_profile(run_history),
                        "chunking": profile_utils.compute_chunking_stability_profile(run_history),
                    }
                    _write_json_safely(Path(".pipeline") / "profiles" / f"stable_profiles_{ts}.json", stable_profiles)

                if enable_genre_learning:
                    genre_profile = profile_utils.compute_genre_profile(run_history, metadata_history)
                    _write_json_safely(Path(".pipeline") / "profiles" / f"genre_profile_{ts}.json", genre_profile)

                if enable_profile_fusion and profile_manager:
                    fused_profile = profile_manager.fuse_profiles(
                        stable_profiles,
                        genre_profile,
                        memory_summary,
                        reward_history,
                    )
                    _write_json_safely(Path(".pipeline") / "profile_history" / f"fused_profile_{ts}.json", fused_profile)

        # Optional export/reset safeguards (manual intent only)
        profiles_cfg = getattr(auto_cfg, "profiles", None) if auto_cfg else None
        if profiles_cfg:
            export_on_shutdown = bool(getattr(profiles_cfg, "export_on_shutdown", False))
            allow_reset = bool(getattr(profiles_cfg, "allow_reset_via_flag", False))
            reset_now = bool(getattr(profiles_cfg, "reset_now", False))

            if export_on_shutdown:
                export_profiles(str(Path(".pipeline") / "profiles" / "exports"))

            if allow_reset and reset_now:
                reset_profiles()
                try:
                    profiles_cfg.reset_now = False
                except Exception:
                    pass

    finally:
        # This block will run whether the pipeline succeeded, failed, or was cancelled.
        logger.info("Running post-pipeline cleanup and finalization...")
        _run_lexicon_updater()
        
        # Health Check
        try:
            from tools.health_check import HealthCheck
            health_checker = HealthCheck(str(pipeline_json), file_id)
            health_report = health_checker.run()
            if health_report["status"] == "unhealthy":
                print_panel(
                    "[bold red]Health Check Report:[/bold red]\n" + "\n".join(f"- {i}" for i in health_report["issues"]),
                    "POST-RUN HEALTH CHECK",
                    "red"
                )
            else:
                print_panel("[bold green]Health Check OK[/bold green]", "POST-RUN HEALTH CHECK", "green")
        except ImportError:
            logger.warning("HealthCheck tool not found, skipping post-run health check.")
        except Exception as e:
            logger.error(f"Error running health check: {e}")

    return {
        "success": True,
        "audiobook_path": str(audiobook_path) if audiobook_path else None,
        "metadata": {
            "file_id": file_id,
            "phases_completed": completed_phases,
            "voice_id": voice_id,
            "tts_engine": tts_engine,
            "mastering_preset": mastering_preset,
            "pipeline_data": file_phase_view,
        },
        "error": None,
    }


def main():
    """Main orchestrator entry point."""
    global _SUPERVISED_OVERRIDES, _AUTONOMOUS_OVERRIDES, _RUN_TRACE
    parser = argparse.ArgumentParser(
        description="Phase 6: Production Orchestrator for Audiobook Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline for a PDF
  python orchestrator.py input/The_Analects_of_Confucius_20240228.pdf

  # Resume from checkpoint
  python orchestrator.py input/book.pdf --pipeline-json=pipeline.json

  # Run specific phases only
  python orchestrator.py input/book.pdf --phases 3 4 5
        """,
    )

    parser.add_argument(
        "file",
        type=Path,
        nargs="?",
        help="Input file path (PDF or ebook). Required unless --export-reference is used.",
    )
    parser.add_argument(
        "--pipeline-json",
        type=Path,
        default=None,
        help="Path to pipeline.json (default: from config.yaml or ../pipeline.json)",
    )
    parser.add_argument(
        "--export-reference",
        action="store_true",
        help="Generate UI capability map + pipeline training book (read-only) and exit",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4, 5],
        help="Phases to run (default: 1 2 3 4 5)",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Disable resume from checkpoint (run all phases)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum retry attempts per phase (default: 2)",
    )
    parser.add_argument(
        "--voice",
        type=str,
        help=(
            "Voice ID for TTS synthesis (e.g., george_mckayland, "
            "landon_elkind). Overrides auto-selection from Phase 3."
        ),
    )
    parser.add_argument(
        "--enable-subtitles",
        action="store_true",
        help="Generate .srt and .vtt subtitles after Phase 5 (optional)",
    )
    parser.add_argument(
        "--phase5-concat-only",
        action="store_true",
        help="Reuse existing enhanced WAVs and only concatenate/encode MP3 in Phase 5",
    )
    parser.add_argument(
        "--use-director",
        action="store_true",
        help="Enable Phase 0: Run the Audiobook Director to create a Production Bible before starting the pipeline.",
    )

    args = parser.parse_args()

    if args.export_reference:
        from tools.book_generator import export_reference_bundle

        config_path = Path(__file__).with_name("config.yaml")
        summary = export_reference_bundle(config_path=config_path, output_dir=Path(".pipeline/reference"))
        print(json.dumps(summary, indent=2))
        return 0

    if args.file is None:
        parser.error("the following arguments are required: file (unless --export-reference is used)")

    orchestrator_config = get_orchestrator_config()
    pipeline_mode = orchestrator_config.pipeline_mode.lower()
    RUN_SUMMARY.update(
        {
            "phase4_reused": False,
            "per_chunk_fallback_used": False,
            "tts_workers_used": None,
            "chunk_integrity_passed": None,
            "backup_subtitles_used": False,
            "budget_exceeded": False,
        }
    )

    # Validate input file (resolve path first)
    file_path = args.file.resolve()
    if not file_path.exists():
        print_status(f"[red]ERROR: File not found: {file_path}[/red]")
        return 1
    file_id = file_path.stem

    # Resolve pipeline.json path
    pipeline_json = (args.pipeline_json or orchestrator_config.pipeline_path).resolve()
    
    # --- Audiobook Director (Phase 0) ---
    if args.use_director:
        print_status("\n[bold magenta]> Running Phase 0 (Audiobook Director)...[/bold magenta]")
        director_success = run_phase_0_director(file_id, file_path, pipeline_json)
        if not director_success:
            print_panel("Audiobook Director (Phase 0) failed. Aborting.", "PIPELINE FAILED", "bold red")
            return 1
        print_status("[green]OK Phase 0 completed successfully[/green]")
    # ------------------------------------

    state = PipelineState(pipeline_json, validate_on_read=False)
    policy_config = orchestrator_config.policy_engine or {}
    policy_engine = PolicyEngine(
        logging_enabled=bool(policy_config.get("logging", False)),
        learning_mode=str(policy_config.get("learning_mode", "observe")),
    )

    # Display header (use -> instead of → for Windows compatibility)
    phases_to_run = args.phases or orchestrator_config.phases_to_run
    phase_display = " -> ".join(map(str, phases_to_run))
    header = f"""
Audiobook Pipeline - Phase 6 Orchestrator

Input File:    {file_path.name}
File ID:       {file_id}
Pipeline JSON: {pipeline_json}
Phases:        {phase_display}
Resume:        {'Disabled' if args.no_resume else 'Enabled'}
Max Retries:   {args.max_retries}
Pipeline Mode: {pipeline_mode}
"""
    print_panel(header.strip(), "Configuration", "bold cyan")

    resume_enabled = not args.no_resume
    policy_phase_timers: Dict[str, float] = {}

    # Configure Phase 5 concat-only hint
    if args.phase5_concat_only:
        os.environ["PHASE5_CONCAT_ONLY"] = "1"
        logger.info("Phase 5: concat-only mode enabled (will reuse enhanced WAVs if present).")
    else:
        os.environ.pop("PHASE5_CONCAT_ONLY", None)

    # Run phases
    overall_start = time.perf_counter()
    global_start = time.time()
    budget_limit = orchestrator_config.global_time_budget_sec
    completed_phases = []

    # Log voice configuration if specified
    if args.voice:
        print_status(f"[cyan]Voice Override: {args.voice}[/cyan]")

    for phase_idx, phase_num in enumerate(phases_to_run):
        phase_name = f"Phase {phase_num}"

        if budget_limit is not None and (time.time() - global_start) > budget_limit:
            RUN_SUMMARY["budget_exceeded"] = True
            logger.warning("Global time budget exceeded, stopping execution.")
            remaining = phases_to_run[phase_idx:]
            for phase_to_skip in remaining:
                mark_phase_skipped(pipeline_json, phase_to_skip)
            break

        # Check resume status
        resume_status: Optional[str] = None
        if resume_enabled:
            resume_status = check_phase_status(state, phase_num, file_id)
            if resume_status == "success":
                print_status(f"[green]OK Skipping {phase_name} (already completed)[/green]")
                completed_phases.append(phase_num)
                continue
            elif resume_status in ["failed", "partial"]:
                print_status(f"[yellow]> Retrying {phase_name} (previous status: {resume_status})[/yellow]")

        # Run phase with retries (use > instead of ▶ for Windows compatibility)
        print_status(f"\n[bold cyan]> Running {phase_name}...[/bold cyan]")

        phase_label = f"phase{phase_num}"
        policy_phase_timers[phase_label] = time.perf_counter()
        start_ctx = _build_policy_context(
            phase_label,
            file_id,
            pipeline_json,
            status="starting",
            event="phase_start",
            state=state,
            extra={"resume_status": resume_status},
        )
        _policy_call(policy_engine, "record_phase_start", start_ctx)

        success = run_phase_with_retry(
            phase_num,
            file_path,
            file_id,
            pipeline_json,
            state=state,
            max_retries=args.max_retries,
            voice_id=args.voice,
            pipeline_mode=pipeline_mode,
            policy_engine=policy_engine,
        )

        if not success:
            failure_duration = _pop_phase_duration(policy_phase_timers, phase_label)
            failure_ctx = _build_policy_context(
                phase_label,
                file_id,
                pipeline_json,
                status="failed",
                event="phase_failure",
                state=state,
                duration_ms=failure_duration,
                include_snapshot=True,
                errors=[f"Phase {phase_num} failed"],
            )
            _policy_call(policy_engine, "record_failure", failure_ctx)
            _log_policy_advice(policy_engine, failure_ctx, phase_label, file_id)
            play_sound(success=False)
            print_panel(
                f"Pipeline aborted at {phase_name}\n\n"
                f"Check logs above for details.\n"
                f"Fix issues and re-run with same command to resume.",
                "PIPELINE FAILED",
                "bold red",
            )
            return 1

        print_status(f"[green]OK {phase_name} completed successfully[/green]")
        play_sound(success=True)

        duration_ms = _pop_phase_duration(policy_phase_timers, phase_label)
        end_ctx = _build_policy_context(
            phase_label,
            file_id,
            pipeline_json,
            status="success",
            event="phase_end",
            state=state,
            duration_ms=duration_ms,
            include_snapshot=True,
        )
        _policy_call(policy_engine, "record_phase_end", end_ctx)
        _log_policy_advice(policy_engine, end_ctx, phase_label, file_id)

        if phase_num == 5:
            archive_final_audiobook(file_id, pipeline_json)
        completed_phases.append(phase_num)

    if RUN_SUMMARY["budget_exceeded"]:
        print_panel(
            "Global time budget exceeded, stopping execution.",
            "TIME BUDGET",
            "bold yellow",
        )
        summarize_results(pipeline_json)
        if policy_engine:
            policy_engine.complete_run(
                success=False,
                metadata={"file_id": file_id, "reason": "budget_exceeded"},
            )
        return 1

    auto_subtitles = getattr(orchestrator_config, "auto_subtitles", False)
    if pipeline_mode == "personal":
        subtitles_enabled = args.enable_subtitles
        if auto_subtitles and not subtitles_enabled:
            logger.info("Personal mode: ignoring auto subtitles. Use --enable-subtitles to run Phase 5.5.")
    else:
        subtitles_enabled = args.enable_subtitles or auto_subtitles

    # Phase 5.5: Generate subtitles (optional)
    if 5 in completed_phases and subtitles_enabled:
        print_status("\n[bold cyan]> Running Phase 5.5 (Subtitles)...[/bold cyan]")
        phase5_dir = find_phase_dir(5)
        if phase5_dir:
            subtitle_phase_label = "phase5.5"
            policy_phase_timers[subtitle_phase_label] = time.perf_counter()
            subtitle_start_ctx = _build_policy_context(
                subtitle_phase_label,
                file_id,
                pipeline_json,
                status="starting",
                event="phase_start",
                state=state,
            )
            _policy_call(policy_engine, "record_phase_start", subtitle_start_ctx)

            success = run_phase5_5_subtitles(phase5_dir, file_id, pipeline_json, enable_subtitles=True)

            duration_ms = _pop_phase_duration(policy_phase_timers, subtitle_phase_label)
            if success:
                print_status("[green]OK Phase 5.5 (Subtitles) completed successfully[/green]")
                subtitle_end_ctx = _build_policy_context(
                    subtitle_phase_label,
                    file_id,
                    pipeline_json,
                    status="success",
                    event="phase_end",
                    state=state,
                    duration_ms=duration_ms,
                    include_snapshot=True,
                )
                _policy_call(policy_engine, "record_phase_end", subtitle_end_ctx)
                _log_policy_advice(
                    policy_engine,
                    subtitle_end_ctx,
                    subtitle_phase_label,
                    file_id,
                )
            else:
                print_status("[yellow]Warning: Phase 5.5 (Subtitles) failed - continuing anyway[/yellow]")
                subtitle_failure_ctx = _build_policy_context(
                    subtitle_phase_label,
                    file_id,
                    pipeline_json,
                    status="failed",
                    event="phase_failure",
                    state=state,
                    duration_ms=duration_ms,
                    include_snapshot=True,
                    errors=["Phase 5.5 (Subtitles) failed"],
                )
                _policy_call(policy_engine, "record_failure", subtitle_failure_ctx)
                _log_policy_advice(
                    policy_engine,
                    subtitle_failure_ctx,
                    subtitle_phase_label,
                    file_id,
                )

    # Optional self-repair stage (post-run)
    try:
        run_postrun_self_repair(
            pipeline_json,
            file_id,
            orchestrator_config.autonomy,
            orchestrator_config.self_repair,
        )
    except Exception as exc:
        logger.warning("Post-run self-repair skipped due to error: %s", exc)

    # Optional reasoning evaluator (post-run summary)
    try:
        run_reasoning_evaluator(
            pipeline_json,
            file_id,
            orchestrator_config.reasoning,
        )
    except Exception as exc:
        logger.warning("Reasoning evaluator skipped: %s", exc)

    # Optional diagnostics (Llama, opt-in)
    try:
        run_reasoning_diagnostics(
            orchestrator_config.reasoning,
            orchestrator_config.autonomy,
        )
    except Exception as exc:
        logger.warning("Diagnostics skipped: %s", exc)

    planner_output: Optional[Dict[str, Any]] = None
    run_trace = _RUN_TRACE
    # Optional autonomy planner (recommend-only)
    try:
        introspection_cfg = orchestrator_config.introspection if hasattr(orchestrator_config, "introspection") else {}
        if not isinstance(introspection_cfg, dict):
            introspection_cfg = {}
        if introspection_cfg.get("enable_reasoning_trace", False) and run_trace is None:
            trace_id = policy_engine.run_id if policy_engine else datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            run_trace = begin_run_trace(trace_id)
            _RUN_TRACE = run_trace
            record_event(run_trace, "run_start", "Run trace initialized", {"run_id": trace_id})

        planner_output = run_autonomy_planner(
            orchestrator_config.autonomy,
            pipeline_json,
            orchestrator_config.genre,
            autonomy_mode=orchestrator_config.autonomy.mode,
        )
        if run_trace is not None:
            record_event(
                run_trace,
                stage="planner",
                message="Planner produced recommendations",
                payload={"recommendations": planner_output},
            )
        autonomy_mode = orchestrator_config.autonomy.mode
        safety_ctx_post = _evaluate_autonomy_safety(
            orchestrator_config,
            planner_output,
            run_id=current_run_id,
            context="planner_output",
        )
        autonomy_mode = safety_ctx_post.get("autonomy_mode", autonomy_mode)
        readiness_report = safety_ctx_post.get("readiness", {})
        filtered_overrides = safety_ctx_post.get("filtered_overrides") or {}
        if planner_output and filtered_overrides:
            if "suggested_changes" in planner_output:
                planner_output["suggested_changes"] = filtered_overrides
            if "autonomous_recommendations" in planner_output:
                planner_output["autonomous_recommendations"]["changes"] = filtered_overrides

        safety_block_overrides = not safety_ctx_post.get("allow_overrides", False)
        if safety_block_overrides:
            _SUPERVISED_OVERRIDES.clear()
            _AUTONOMOUS_OVERRIDES.clear()
        # Supervised autonomy budget enforcement (in-memory only)
        if (
            autonomy_mode == "supervised"
            and planner_output
            and safety_ctx_post.get("allow_overrides", False)
            and planner_output.get("confidence", 0.0) >= orchestrator_config.autonomy.supervised_threshold
        ):
            try:
                budgeted = {
                    "suggested_changes": filtered_overrides,
                    "confidence": planner_output.get("confidence"),
                }
                if not safety_block_overrides:
                    _SUPERVISED_OVERRIDES = {
                        "overrides": budgeted.get("suggested_changes") if filtered_overrides else {},
                        "confidence": budgeted.get("confidence", planner_output.get("confidence")),
                        "source": "supervised_mode",
                    }
            except Exception:
                pass
        # Autonomous mode temporary overrides (opt-in, in-memory only)
        elif (
            autonomy_mode == "autonomous"
            and planner_output
            and safety_ctx_post.get("allow_overrides", False)
        ):
            try:
                if not safety_block_overrides:
                    _SUPERVISED_OVERRIDES = {
                        "overrides": filtered_overrides,
                        "confidence": planner_output.get("confidence", 0.0),
                        "source": "autonomous_mode",
                    }
            except Exception:
                pass
        # Policy limits (opt-in) filter supervised overrides
        if (
            orchestrator_config.autonomy.enable_policy_limits
            and planner_output
            and _SUPERVISED_OVERRIDES.get("overrides")
        ):
            try:
                from autonomy.autonomy_policy import check_policy

                filtered = check_policy(_SUPERVISED_OVERRIDES.get("overrides"))
                _SUPERVISED_OVERRIDES["overrides"] = filtered
            except Exception:
                pass
        journal_recorded = False
        # Readiness assessment (opt-in reporting only)
        if orchestrator_config.autonomy.readiness_checks.get("enable", False):
            try:
                from autonomy import readiness
                from autonomy import reinforcement

                summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
                evaluator_summary = {}
                if summary_path.exists():
                    evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
                diagnostics_output = {}
                diag_dir = Path(".pipeline") / "diagnostics"
                latest_diag = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if latest_diag:
                    diagnostics_output = json.loads(latest_diag[0].read_text(encoding="utf-8"))
                from policy_engine.policy_engine import get_benchmark_history

                bench = get_benchmark_history()
                recent_rewards = reinforcement.load_recent_rewards()
                ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                readiness_report = readiness.assess_readiness(
                    evaluator_summary,
                    diagnostics_output,
                    bench,
                    recent_rewards,
                    orchestrator_config.autonomy.readiness_checks,
                )
                out_dir = Path(".pipeline") / "policy_runtime"
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / f"autonomy_readiness_{ts}.json").write_text(
                    json.dumps(readiness_report, indent=2), encoding="utf-8"
                )
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Autonomy planner skipped: %s", exc)

    # Optional feature attribution for planner output (opt-in)
    try:
        introspection_cfg = orchestrator_config.introspection if hasattr(orchestrator_config, "introspection") else {}
        if not isinstance(introspection_cfg, dict):
            introspection_cfg = {}
        if introspection_cfg.get("enable_feature_attribution", False) and planner_output:
            summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
            evaluator_summary = {}
            if summary_path.exists():
                try:
                    evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
                except Exception:
                    evaluator_summary = {}
            diagnostics_output = {}
            diag_dir = Path(".pipeline") / "diagnostics"
            latest_diag = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if latest_diag:
                try:
                    diagnostics_output = json.loads(latest_diag[0].read_text(encoding="utf-8"))
                except Exception:
                    diagnostics_output = {}
            attribution = explain_recommendations(
                planner_output,
                {},
                evaluator_summary,
                diagnostics_output,
            )
            planner_output["attribution"] = attribution
            if _RUN_TRACE is not None:
                record_event(_RUN_TRACE, "attribution", "Feature attribution generated", {"attribution": attribution})
    except Exception:
        pass

    # Optional benchmark auto-run (non-blocking, opt-in)
    try:
        if orchestrator_config.benchmark.enable and orchestrator_config.benchmark.auto_run:
            from phaseE_benchmark.benchmark_runner import BenchmarkRunner

            BenchmarkRunner().run_all_engines()
    except Exception as exc:
        logger.warning("Benchmark auto-run skipped due to error: %s", exc)

    # Optional post-run log parsing and repair loop (non-destructive)
    try:
        repairs_applied = run_postrun_repair_pipeline(
            pipeline_json,
            file_id,
            orchestrator_config.self_repair,
        )
        if (
            orchestrator_config.self_repair.enable_engine_retry
            and repairs_applied
            and isinstance(repairs_applied, list)
        ):
            from phase4_tts.engines.engine_manager import EngineManager

            manager = EngineManager()
            filtered = [
                r for r in repairs_applied if r.get("confidence", 0.0) >= orchestrator_config.self_repair.retry_confidence_threshold
            ]
            for repair in filtered:
                manager.try_repaired_chunk(repair.get("chunk"), repair)
        # Update run summary with repairs applied (non-destructive)
        try:
            summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
            evaluator_summary = {}
            if summary_path.exists():
                evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
            diagnostics_output = {}
            diag_dir = Path(".pipeline") / "diagnostics"
            latest_diag = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if latest_diag:
                diagnostics_output = json.loads(latest_diag[0].read_text(encoding="utf-8"))
            if repairs_applied and summary_path.exists():
                summary = evaluator_summary or {}
                summary["repairs_applied"] = [
                    {
                        "chunk_id": r.get("chunk"),
                        "audio_path": r.get("path"),
                        "confidence": r.get("confidence"),
                        "notes": r.get("notes", ""),
                    }
                    for r in repairs_applied
                ]
                summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            reward_for_memory: Optional[float] = None
            # Rewards (opt-in)
            if orchestrator_config.autonomy.enable_rewards:
                try:
                    from autonomy import reinforcement, memory_store

                    prev = memory_store.load_previous_run()
                    reward = reinforcement.compute_reward(evaluator_summary, diagnostics_output, prev)
                    reward_for_memory = reward.get("reward")
                    reinforcement.save_reward(reward)
                    # Record autonomy change journal (informational)
                    try:
                        from autonomy.rollback import record_changes

                        run_id = policy_engine.run_id if policy_engine else current_run_id
                        applied_overrides = (
                            _AUTONOMOUS_OVERRIDES.get("overrides")
                            or _SUPERVISED_OVERRIDES.get("overrides", {})
                        )
                        record_changes(run_id, applied_overrides or {}, reward.get("reward", 0.0))
                        journal_recorded = True
                    except Exception:
                        pass
                except Exception:
                    pass
            # Self-review (opt-in, reflective only)
            if orchestrator_config.autonomy.enable_self_review:
                try:
                    from agents.llama_self_review import LlamaSelfReview
                    from autonomy import memory_store

                    run_history = memory_store.load_run_history(limit=5)

                    reflection = (
                        LlamaSelfReview()
                        .analyze_run(
                            evaluator_summary or {},
                            diagnostics_output or {},
                            {"history": run_history},
                            planner_output or {},
                        )
                        or {}
                    )
                    refl_dir = Path(".pipeline") / "reflections"
                    refl_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    (refl_dir / f"{ts}.json").write_text(json.dumps(reflection, indent=2), encoding="utf-8")
                    policy_refl_dir = Path(".pipeline") / "policy_runtime" / "reflections"
                    policy_refl_dir.mkdir(parents=True, exist_ok=True)
                    (policy_refl_dir / f"{ts}.json").write_text(json.dumps(reflection, indent=2), encoding="utf-8")
                except Exception:
                    pass
            # Memory feedback: persist run performance (opt-in, always run at end, after reward/review)
            if orchestrator_config.autonomy.enable_memory_feedback:
                try:
                    from autonomy import memory_store

                    phase_failures = evaluator_summary.get("phase_failures", {}) if isinstance(evaluator_summary, dict) else {}
                    engine_used = evaluator_summary.get("engine_used") if isinstance(evaluator_summary, dict) else None
                    chunk_settings = evaluator_summary.get("chunk_settings") if isinstance(evaluator_summary, dict) else {}
                    duration_seconds = evaluator_summary.get("duration_seconds") if isinstance(evaluator_summary, dict) else None
                    memory_store.record_run_performance(
                        current_run_id,
                        file_id,
                        evaluator_summary or {},
                        diagnostics_output or {},
                        reward=reward_for_memory,
                        engine_used=engine_used,
                        chunk_settings=chunk_settings,
                        duration_seconds=duration_seconds,
                        phase_failures=phase_failures,
                    )
                except Exception:
                    pass
            # Stability profiles (opt-in)
            if orchestrator_config.autonomy.enable_stability_profiles:
                try:
                    from autonomy import memory_store

                    run_history = memory_store.load_run_history(limit=50)
                    profiles = {
                        "engine_stability": memory_store.extract_engine_stability_patterns(run_history),
                        "genre_stability": memory_store.extract_genre_stability(run_history),
                        "chunk_size_stability": memory_store.extract_chunk_size_stability(run_history),
                        "summary": "Stability snapshot derived from recent runs.",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    out_dir = Path(".pipeline") / "stability_profiles"
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / f"stability_{ts}.json").write_text(json.dumps(profiles, indent=2), encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            pass
        # Record journal for autonomous overrides even if rewards are disabled
        if not journal_recorded and _AUTONOMOUS_OVERRIDES:
            try:
                from autonomy.rollback import record_changes

                run_id = policy_engine.run_id if policy_engine else "unknown"
                record_changes(run_id, _AUTONOMOUS_OVERRIDES.get("overrides", {}), 0.0)
            except Exception:
                pass
    except Exception as exc:
        logger.warning("Post-run repair loop skipped: %s", exc)

    # Record experiment result (if any)
    try:
        if orchestrator_config.experiments.enable and orchestrator_config.autonomy.memory_enabled:
            from autonomy.memory_store import add_experience

            add_experience(
                "experiment_result",
                {
                    "file_id": file_id,
                    "status": "completed",
                },
            )
        if orchestrator_config.experiments.enable:
            _reset_experiment_state()
        # Persist supervised actions (if any) then reset
        combined_overrides = _AUTONOMOUS_OVERRIDES or _SUPERVISED_OVERRIDES
        if combined_overrides:
            run_id = policy_engine.run_id if policy_engine else datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            out_dir = Path(".pipeline") / "policy_runtime" / "supervised_actions"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{run_id}.json"
            payload = {
                "overrides": combined_overrides.get("overrides"),
                "confidence": combined_overrides.get("confidence"),
                "notes": "Temporary overrides only; no changes persisted.",
                "source": combined_overrides.get("source"),
            }
            out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            _reset_supervised_overrides()
    except Exception:
        pass

    # Phase I introspection (opt-in, additive-only)
    try:
        introspection_cfg = orchestrator_config.introspection if hasattr(orchestrator_config, "introspection") else {}
        if not isinstance(introspection_cfg, dict):
            introspection_cfg = {}

        if any(
            introspection_cfg.get(flag, False)
            for flag in ("enable_clustering", "enable_narratives", "enable_self_critique", "enable_summary")
        ):
            try:
                from autonomy import memory_store
            except Exception:
                memory_store = None

            summary_path = Path(".pipeline") / "policy_runtime" / "last_run_summary.json"
            evaluator_summary = {}
            if summary_path.exists():
                try:
                    evaluator_summary = json.loads(summary_path.read_text(encoding="utf-8"))
                except Exception:
                    evaluator_summary = {}
            diagnostics_output = {}
            diag_dir = Path(".pipeline") / "diagnostics"
            latest_diag = sorted(diag_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            if latest_diag:
                try:
                    diagnostics_output = json.loads(latest_diag[0].read_text(encoding="utf-8"))
                except Exception:
                    diagnostics_output = {}
            planner_recommendations = planner_output or {}
            run_history = memory_store.load_run_history(limit=5) if memory_store and hasattr(memory_store, "load_run_history") else []

            clusters = None
            narrative = None
            critique = None

            if introspection_cfg.get("enable_clustering", False):
                try:
                    clusters = cluster_anomalies(evaluator_summary, diagnostics_output, run_history)
                except Exception:
                    clusters = {}
            if introspection_cfg.get("enable_narratives", False):
                try:
                    narrative = generate_narrative(clusters, evaluator_summary, diagnostics_output)
                except Exception:
                    narrative = {}
            if introspection_cfg.get("enable_self_critique", False):
                try:
                    critique = self_critique(evaluator_summary, diagnostics_output, planner_recommendations, clusters)
                except Exception:
                    critique = {}
            if introspection_cfg.get("enable_summary", False):
                try:
                    run_id = policy_engine.run_id if policy_engine else datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                except Exception:
                    run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                bundle = auto_introspection.build_introspection_summary(
                    planner_recommendations,
                    evaluator_summary,
                    diagnostics_output,
                    None,
                )
                _write_json_safely(Path(".pipeline") / "introspection" / f"{run_id}_introspection.json", bundle)
                if _RUN_TRACE is not None:
                    record_event(
                        _RUN_TRACE,
                        "introspection_summary",
                        "Introspection summary written",
                        {"path": str(Path(".pipeline") / "introspection" / f"{run_id}_introspection.json")},
                    )
    except Exception:
        pass

    # Finalize reasoning trace (if enabled)
    try:
        if _RUN_TRACE is not None:
            try:
                trace_run_id = _RUN_TRACE.get("run_id") if isinstance(_RUN_TRACE, dict) else None
                if not trace_run_id:
                    trace_run_id = policy_engine.run_id if policy_engine else datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            except Exception:
                trace_run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            finalize_trace(_RUN_TRACE, str(Path(".pipeline") / "traces" / f"{trace_run_id}_trace.json"))
    except Exception:
        pass

    # Long-horizon aggregation and forecasting (opt-in, informational only)
    try:
        auto_cfg = orchestrator_config.autonomy
    except Exception:
        auto_cfg = None
    try:
        enable_long_horizon = bool(getattr(auto_cfg, "enable_long_horizon", False)) if auto_cfg else False
        enable_forecasting = bool(getattr(auto_cfg, "enable_forecasting", False)) if auto_cfg else False
        enable_long_profiles = bool(getattr(auto_cfg, "enable_long_horizon_profiles", False)) if auto_cfg else False
        enable_trend_modeling = bool(getattr(auto_cfg, "enable_trend_modeling", False)) if auto_cfg else False
        long_horizon_snapshot = None
        patterns_path = None
        forecast_path = None
        snapshot_path = None
        pointer_data = {}
        if enable_long_horizon or enable_forecasting or enable_long_profiles or enable_trend_modeling:
            summaries = lh_aggregator.load_all_runs()
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            patterns_result = None
            if enable_long_horizon:
                long_horizon_snapshot = lh_aggregator.aggregate_long_horizon_history(summaries)
                snapshot_path = lh_aggregator.write_long_horizon_snapshot(long_horizon_snapshot, ts)
                patterns_result = lh_patterns.build_cross_run_patterns(summaries)
                if patterns_result:
                    patterns_out = Path(".pipeline") / "long_horizon" / f"patterns_{ts}.json"
                    _write_json_safely(patterns_out, patterns_result)
                    patterns_path = patterns_out
            if enable_long_profiles:
                profile = auto_long_horizon.aggregate_multi_run_history(summaries)
                auto_long_horizon.write_long_horizon_profile(profile, ts)
            trend_info = None
            if enable_trend_modeling:
                trend_info = auto_trends.build_combined_trends(summaries)
                trends_out = Path(".pipeline") / "policy_runtime" / f"trends_{ts}.json"
                _write_json_safely(trends_out, trend_info)
            if enable_forecasting:
                if trend_info is None:
                    trend_info = auto_trends.build_combined_trends(summaries)
                forecast = auto_predictive.forecast_outcomes(summaries, trend_info or {})
                forecast_out = Path(".pipeline") / "policy_runtime" / f"forecast_{ts}.json"
                _write_json_safely(forecast_out, forecast)
                forecast_path = forecast_out
                if planner_output and isinstance(planner_output, dict):
                    planner_output["forecast"] = forecast
            if enable_long_horizon or enable_forecasting or enable_long_profiles or enable_trend_modeling:
                pointer_data = {
                    "snapshot_file": str(snapshot_path) if snapshot_path else None,
                    "patterns_file": str(patterns_path) if patterns_path else None,
                    "forecast_file": str(forecast_path) if forecast_path else None,
                    "timestamp": ts,
                }
                pointer_out = Path(".pipeline") / "policy_runtime" / f"long_horizon_summary_{ts}.json"
                _write_json_safely(pointer_out, pointer_data)
    except Exception:
        pass

    # Calculate duration
    duration = time.perf_counter() - overall_start

    # Display summary (use -> instead of → for Windows compatibility)
    phases_display = " -> ".join(map(str, completed_phases))
    # Precompute some display strings to keep summary lines short
    chunk_integrity_display = (
        "passed"
        if RUN_SUMMARY.get("chunk_integrity_passed")
        else ("skipped" if RUN_SUMMARY.get("chunk_integrity_passed") is None else "failed")
    )

    summary = f"""
Pipeline completed successfully!

Phases Completed: {phases_display}
Total Duration:   {duration:.1f}s ({duration/60:.1f} minutes)
Phase 4 reuse:    {"reused" if RUN_SUMMARY.get("phase4_reused") else "rerun"}
Per-chunk fallback used: {"yes" if RUN_SUMMARY.get("per_chunk_fallback_used") else "no"}
TTS workers used: {RUN_SUMMARY.get("tts_workers_used") or 1}
Chunk integrity:  {chunk_integrity_display}
Backup subtitles: {"yes" if RUN_SUMMARY.get("backup_subtitles_used") else "no"}
Time budget hit:  { "yes" if RUN_SUMMARY.get("budget_exceeded") else "no"}

Output Location:
- Chunks: phase3-chunking/chunks/
- Audio:  phase4_tts/audio_chunks/
- Final:  phase5_enhancement/processed/
- Subtitles: phase5_enhancement/subtitles/ (if enabled)

Next Steps:
1. Review pipeline.json for quality metrics
2. Listen to final audiobook in phase5_enhancement/processed/
3. Check for any warnings in logs above
"""
    print_panel(summary.strip(), "SUCCESS", "bold green")

    # Show results table
    summarize_results(pipeline_json)

    if policy_engine:
        policy_engine.complete_run(
            success=True,
            metadata={"file_id": file_id, "phases": completed_phases},
        )

    # Optional Phase P research hook (opt-in, non-blocking)
    try:
        research_cfg = getattr(orchestrator_config, "research", None)
        research_enabled = False
        if isinstance(research_cfg, dict):
            research_enabled = bool(research_cfg.get("enable"))
        else:
            research_enabled = bool(getattr(research_cfg, "enable", False))
        if research_enabled:
            from phaseP_research.research_config import ResearchConfig
            from phaseP_research.research_collector import ResearchCollector
            from phaseP_research.research_analyzer import ResearchAnalyzer
            from phaseP_research.research_reporter import ResearchReporter
            from phaseP_research.init import initialize_research_state

            cfg_kwargs = {
                "enable_research": research_enabled,
                "collect_phase_metrics": bool(getattr(research_cfg, "collect_phase_metrics", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_phase_metrics")),
                "collect_failure_patterns": bool(getattr(research_cfg, "collect_failure_patterns", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_failure_patterns")),
                "collect_engine_stats": bool(getattr(research_cfg, "collect_engine_stats", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_engine_stats")),
                "collect_chunk_stats": bool(getattr(research_cfg, "collect_chunk_stats", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_chunk_stats")),
                "collect_memory_signals": bool(getattr(research_cfg, "collect_memory_signals", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_memory_signals")),
                "collect_policy_signals": bool(getattr(research_cfg, "collect_policy_signals", False))
                if not isinstance(research_cfg, dict)
                else bool(research_cfg.get("collect_policy_signals")),
            }
            rcfg = ResearchConfig(**cfg_kwargs)
            try:
                state = PipelineState(pipeline_json, validate_on_read=False)
                run_state = state.read(validate=False)
            except Exception:
                run_state = {}
            try:
                initialize_research_state(Path(".pipeline") / "research")
            except Exception:
                pass
            # Observations per phase (read-only)
            try:
                from phaseP_research.observation_hooks import record_phase_observation

                for phase_key, pdata in run_state.items():
                    if not isinstance(pdata, dict) or not phase_key.startswith("phase"):
                        continue
                    observation_payload = {
                        "input_size": pdata.get("input_size") or pdata.get("metrics", {}).get("files_processed") if isinstance(pdata.get("metrics"), dict) else None,
                        "output_size": pdata.get("metrics", {}).get("files_processed") if isinstance(pdata.get("metrics"), dict) else None,
                        "metadata": {
                            "status": pdata.get("status"),
                        },
                    }
                    record_phase_observation(phase_key, observation_payload, rcfg)
            except Exception:
                pass
            raw = ResearchCollector(rcfg).collect(run_state)
            analysis = ResearchAnalyzer().analyze(raw)
            ResearchReporter().write_report(analysis)

            research_signals = {"raw": raw, "analysis": analysis}
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

            # Quality gate (informational only)
            try:
                enable_qg = False
                if isinstance(research_cfg, dict):
                    enable_qg = bool(research_cfg.get("enable_quality_gate"))
                else:
                    enable_qg = bool(getattr(research_cfg, "enable_quality_gate", False))
                if enable_qg:
                    from phaseP_research.quality_gate import (
                        evaluate_quality_gate,
                        write_quality_gate,
                    )

                    qg_result = evaluate_quality_gate(research_signals, run_state)
                    write_quality_gate(qg_result)
            except Exception:
                pass

            # Research feedback loop (append-only)
            try:
                enable_feedback = False
                if isinstance(research_cfg, dict):
                    enable_feedback = bool(research_cfg.get("enable_feedback_loop"))
                else:
                    enable_feedback = bool(getattr(research_cfg, "enable_feedback_loop", False))
                if enable_feedback:
                    from phaseP_research.feedback_loop import update_research_feedback

                    update_research_feedback({}, research_signals)
            except Exception:
                pass

            # Safety verification (informational)
            try:
                enable_safety = False
                if isinstance(research_cfg, dict):
                    enable_safety = bool(research_cfg.get("enable_safety_verification"))
                else:
                    enable_safety = bool(getattr(research_cfg, "enable_safety_verification", False))
                if enable_safety:
                    from phaseP_research.safety_verification import verify_research_outputs

                    verify_research_outputs(research_signals)
            except Exception:
                pass

            # Research lifecycle controller (opt-in)
            try:
                enable_lifecycle = False
                if isinstance(research_cfg, dict):
                    enable_lifecycle = bool(research_cfg.get("enable_lifecycle"))
                else:
                    enable_lifecycle = bool(getattr(research_cfg, "enable_lifecycle", False))
                if enable_lifecycle:
                    from phaseP_research.research_runner import ResearchRunner

                    runner = ResearchRunner(research_cfg)
                    runner.begin_run()
                    evidence = runner.ingest_evidence(run_state, [])
                    patterns = runner.extract_patterns(evidence)
                    runner.write_report({"raw": raw, "analysis": analysis, "patterns": patterns})
            except Exception:
                pass
            except Exception:
                pass

            # Phase Q self-evaluation (opt-in, informational)
            try:
                phaseq_cfg = getattr(orchestrator_config, "phaseQ_self_evaluation", None) or getattr(orchestrator_config, "phaseQ_self_eval", None)
                phaseq_enabled = False
                output_dir = ".pipeline/self_evaluation"
                if isinstance(phaseq_cfg, dict):
                    phaseq_enabled = bool(phaseq_cfg.get("enable"))
                    output_dir = phaseq_cfg.get("output_dir", output_dir)
                else:
                    phaseq_enabled = bool(getattr(phaseq_cfg, "enable", False))
                    output_dir = getattr(phaseq_cfg, "output_dir", output_dir)
                if phaseq_enabled:
                    try:
                        from phaseQ_self_evaluation import metrics_engine, report_writer
                        errors_log = Path(output_dir) / "errors.log"
                        Path(output_dir).mkdir(parents=True, exist_ok=True)
                        long_horizon_state = {}
                        metrics = metrics_engine.compute_metrics(RUN_SUMMARY, long_horizon_state)
                        run_id = policy_engine.run_id if policy_engine else datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        report_writer.write_report(run_id, metrics, output_dir)
                    except Exception as exc:
                        try:
                            (Path(output_dir) / "errors.log").write_text(str(exc), encoding="utf-8")
                        except Exception:
                            pass
            except Exception:
                pass

            # Phase Q Steps 5-7: meta-evaluator and reflection (opt-in)
            try:
                meta_cfg = getattr(orchestrator_config, "phaseQ_self_eval", None)
                if isinstance(meta_cfg, dict):
                    enable_meta = bool(meta_cfg.get("enable_meta_evaluator"))
                    enable_reflect = bool(meta_cfg.get("enable_reflection_writer"))
                    out_dir = meta_cfg.get("output_dir", ".pipeline/self_eval")
                else:
                    enable_meta = bool(getattr(meta_cfg, "enable_meta_evaluator", False))
                    enable_reflect = bool(getattr(meta_cfg, "enable_reflection_writer", False))
                    out_dir = getattr(meta_cfg, "output_dir", ".pipeline/self_eval")

                meta_result = None
                if enable_meta:
                    try:
                        from phaseQ_self_eval import q_meta_evaluator
                        aggregated_signals = {
                            "research": analysis,
                            "forecasting": {},
                            "stability": {},
                            "rewards": {},
                            "planner": {},
                        }
                        meta_result = q_meta_evaluator.evaluate_meta(aggregated_signals)
                    except Exception:
                        meta_result = None

                if enable_reflect and meta_result is not None:
                    try:
                        from phaseQ_self_eval import reflection_writer
                        reflection_writer.write_reflection(meta_result, Path(out_dir))
                    except Exception:
                        pass
            except Exception:
                pass

            # Phase Q reporting (opt-in, read-only)
            try:
                autonomy_cfg = getattr(orchestrator_config, "autonomy", None)
                self_eval_cfg = getattr(autonomy_cfg, "self_eval", None) if autonomy_cfg else None
                if isinstance(self_eval_cfg, dict):
                    self_eval_enabled = bool(self_eval_cfg.get("enable"))
                else:
                    self_eval_enabled = bool(getattr(self_eval_cfg, "enable", False))
                if self_eval_enabled:
                    from phaseQ_self_eval import cross_phase_fusion, rating_explainer, self_eval_kernel, self_eval_reporter

                    run_id = None
                    try:
                        run_id = policy_engine.run_id if policy_engine else None
                    except Exception:
                        run_id = None
                    run_id = run_id or file_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")

                    kernel_result = self_eval_kernel.evaluate_run({"metrics": RUN_SUMMARY})
                    fusion_result = cross_phase_fusion.fuse_phase_outputs(RUN_SUMMARY)
                    explanation = rating_explainer.explain_rating(kernel_result.get("dimensions", {}), kernel_result.get("overall_rating", 0.0))
                    out_path = self_eval_reporter.write_self_eval_report(
                        run_id,
                        kernel_result,
                        kernel_result.get("overall_rating"),
                        fusion_result,
                        explanation,
                        output_dir=None,
                    )
                    logger.info("Phase Q self-eval: rating=%s", kernel_result.get("overall_rating"))
                    logger.debug("Phase Q self-eval written to %s", out_path)
            except Exception:
                pass

            # Phase R retrospective intelligence (opt-in, read-only)
            try:
                phase_r_cfg = getattr(orchestrator_config, "phaseR", None)
                if isinstance(phase_r_cfg, dict):
                    phase_r_enabled = bool(phase_r_cfg.get("enable"))
                else:
                    phase_r_enabled = bool(getattr(phase_r_cfg, "enable", False))
                if phase_r_enabled:
                    from phaseR_retro import init_state, research_runner

                    init_state.ensure_research_state(Path(".pipeline"))
                    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    research_runner.begin_run(run_id)
                    evidence = research_runner.ingest_evidence(run_id)
                    derived = research_runner.extract_patterns(run_id, evidence)
                    research_runner.write_report(run_id, evidence, derived)
            except Exception:
                pass

            # Phase S review (opt-in, read-only)
            try:
                phase_s_cfg = getattr(orchestrator_config, "phaseS", None)
                if isinstance(phase_s_cfg, dict):
                    phase_s_enabled = bool(phase_s_cfg.get("enable"))
                else:
                    phase_s_enabled = bool(getattr(phase_s_cfg, "enable", False))
                if phase_s_enabled:
                    from phaseS_review import review_kernel, review_aggregator, review_reporter

                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    run_id = ts
                    review = review_kernel.review_run(RUN_SUMMARY)
                    aggregate = review_aggregator.aggregate_reviews([review])
                    review_reporter.write_review_report(run_id, review, aggregate, base_dir=Path(".pipeline/review/reports"))
            except Exception:
                pass

            # Phase T consistency (opt-in, read-only)
            try:
                consistency_cfg = getattr(orchestrator_config, "consistency", None)
                if isinstance(consistency_cfg, dict):
                    consistency_enabled = bool(consistency_cfg.get("enable"))
                else:
                    consistency_enabled = bool(getattr(consistency_cfg, "enable", False))
                if consistency_enabled:
                    from phaseT_consistency import consistency_checker, drift_monitor, health_reporter, schema_registry

                    run_id = None
                    try:
                        run_id = policy_engine.run_id if policy_engine else None
                    except Exception:
                        run_id = None
                    run_id = run_id or file_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    consistency = consistency_checker.check_consistency(RUN_SUMMARY, schema_registry)
                    drift = drift_monitor.detect_system_drift(Path(".pipeline"))
                    health_reporter.write_consistency_report(run_id=run_id, consistency=consistency, drift=drift)
            except Exception:
                pass

            # Phase T audit (opt-in, read-only)
            try:
                phase_t_cfg = getattr(orchestrator_config, "phaseT", None)
                if isinstance(phase_t_cfg, dict):
                    phase_t_enabled = bool(phase_t_cfg.get("enable"))
                else:
                    phase_t_enabled = bool(getattr(phase_t_cfg, "enable", False))
                if phase_t_enabled:
                    from phaseT_audit import audit_kernel, eval_synthesizer, risk_classifier, audit_reporter

                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    run_id = None
                    try:
                        run_id = policy_engine.run_id if policy_engine else None
                    except Exception:
                        run_id = None
                    run_id = run_id or file_id or ts
                    kernel_out = audit_kernel.evaluate_run(RUN_SUMMARY, RUN_SUMMARY)
                    synthesized = eval_synthesizer.synthesize_evaluation(kernel_out, RUN_SUMMARY)
                    risk = risk_classifier.classify(synthesized)
                    report = {
                        "id": ts,
                        "run_id": run_id,
                        "kernel": kernel_out,
                        "synthesized": synthesized,
                        "risk": risk,
                        "created_at": ts,
                        "notes": "Phase T audit",
                    }
                    audit_reporter.write_audit_report(report)
            except Exception:
                pass

            # Phase U safety-integrity (opt-in, read-only)
            try:
                phase_u_cfg = getattr(orchestrator_config, "phaseU", None)
                if isinstance(phase_u_cfg, dict):
                    phase_u_enabled = bool(phase_u_cfg.get("enable"))
                else:
                    phase_u_enabled = bool(getattr(phase_u_cfg, "enable", False))
                if phase_u_enabled:
                    from phaseU_integrity import consistency_unifier, integrity_kernel, integrity_reporter, signal_hub

                    run_id = None
                    try:
                        run_id = policy_engine.run_id if policy_engine else None
                    except Exception:
                        run_id = None
                    run_id = run_id or file_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    signals = signal_hub.collect_signals(run_id, base_dir=".pipeline")
                    integrity = integrity_kernel.evaluate_integrity(
                        RUN_SUMMARY,
                        signals["signals"].get("readiness"),
                        signals["signals"].get("stability"),
                        signals["signals"].get("drift"),
                        signals["signals"].get("self_eval"),
                        signals["signals"].get("retrospection"),
                        signals["signals"].get("review"),
                        signals["signals"].get("audit"),
                    )
                    unified = consistency_unifier.unify(signals, integrity)
                    integrity_reporter.write_integrity_report(unified, base_dir=".pipeline/safety_integrity/reports/")
            except Exception:
                pass

            # Phase V migrations (opt-in, non-destructive)
            try:
                phase_v_cfg = getattr(orchestrator_config, "phaseV", None)
                if isinstance(phase_v_cfg, dict):
                    phase_v_enabled = bool(phase_v_cfg.get("enable"))
                    dry_run = bool(phase_v_cfg.get("dry_run", True))
                else:
                    phase_v_enabled = bool(getattr(phase_v_cfg, "enable", False))
                    dry_run = bool(getattr(phase_v_cfg, "dry_run", True))
                if phase_v_enabled:
                    from phaseV_migrations import migration_reporter, migration_runner

                    plan = migration_runner.plan_migrations(phase_v_cfg, base_dir=Path(".pipeline"))
                    migration_reporter.write_plan_report(plan, base_dir=Path(".pipeline/migrations"))
                    if not dry_run:
                        result = migration_runner.apply_migrations(phase_v_cfg, base_dir=Path(".pipeline"))
                        migration_reporter.write_apply_report(result, base_dir=Path(".pipeline/migrations"))
            except Exception:
                pass

            # Phase W global consistency (opt-in, read-only)
            try:
                phase_w_cfg = getattr(orchestrator_config, "phaseW", None)
                if isinstance(phase_w_cfg, dict):
                    phase_w_enabled = bool(phase_w_cfg.get("enable"))
                else:
                    phase_w_enabled = bool(getattr(phase_w_cfg, "enable", False))
                if phase_w_enabled:
                    from phaseW_global import cross_phase_consistency, global_analyzer, schema_linter, w_reporter

                    # Collect schemas best-effort from run summary; degrade gracefully.
                    phase_schemas = {
                        "phase1": RUN_SUMMARY.get("phase1") if isinstance(RUN_SUMMARY, dict) else None,
                        "phase2": RUN_SUMMARY.get("phase2") if isinstance(RUN_SUMMARY, dict) else None,
                        "phase3": RUN_SUMMARY.get("phase3") if isinstance(RUN_SUMMARY, dict) else None,
                        "phase4": RUN_SUMMARY.get("phase4") if isinstance(RUN_SUMMARY, dict) else None,
                        "phase5": RUN_SUMMARY.get("phase5") if isinstance(RUN_SUMMARY, dict) else None,
                        "phase6": RUN_SUMMARY.get("phase6") if isinstance(RUN_SUMMARY, dict) else None,
                    }
                    lint = schema_linter.lint_schemas(phase_schemas)
                    consistency = cross_phase_consistency.analyze_consistency(phase_schemas)
                    global_info = global_analyzer.global_analysis(lint, consistency)
                    report_payload = {
                        "lint": lint,
                        "consistency": consistency,
                        "global_analysis": global_info,
                        "notes": "Phase W global consistency layer",
                    }
                    w_reporter.write_phaseW_report(report_payload, base_dir=Path(".pipeline/phaseW/reports"))
            except Exception:
                pass

            # Phase X meta-evaluator (opt-in, read-only)
            try:
                phase_x_cfg = getattr(orchestrator_config, "phaseX", None)
                if isinstance(phase_x_cfg, dict):
                    phase_x_enabled = bool(phase_x_cfg.get("enable"))
                    max_depth = int(phase_x_cfg.get("max_depth", 3))
                else:
                    phase_x_enabled = bool(getattr(phase_x_cfg, "enable", False))
                    max_depth = int(getattr(phase_x_cfg, "max_depth", 3))
                if phase_x_enabled:
                    from phaseX_meta import meta_kernel, meta_fusion, meta_ranking, meta_reporter

                    # Load best-effort signals from prior phases (if present in RUN_SUMMARY or elsewhere)
                    inputs = {
                        "self_eval": RUN_SUMMARY.get("phaseQ") if isinstance(RUN_SUMMARY, dict) else {},
                        "retro": RUN_SUMMARY.get("phaseR") if isinstance(RUN_SUMMARY, dict) else {},
                        "review": RUN_SUMMARY.get("phaseS") if isinstance(RUN_SUMMARY, dict) else {},
                    }
                    kernel_out = meta_kernel.evaluate_signal_layers(inputs)
                    fusion_out = meta_fusion.fuse_meta_context(kernel_out)
                    ranking_out = meta_ranking.rank_meta_findings(kernel_out, fusion_out, max_depth=max_depth)
                    report = {
                        "id": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                        "timestamp": datetime.utcnow().strftime("%Y%m%d_%H%M%S"),
                        "kernel": kernel_out,
                        "fusion": fusion_out,
                        "ranking": ranking_out,
                        "summary": "Phase X meta-evaluator report",
                    }
                    meta_reporter.write_meta_report(report, base_dir=Path(".pipeline/meta/reports"))
            except Exception:
                pass

            # Phase Y self-healing (opt-in, read-only; no auto-actions)
            try:
                phase_y_cfg = getattr(orchestrator_config, "phaseY", None)
                if isinstance(phase_y_cfg, dict):
                    phase_y_enabled = bool(phase_y_cfg.get("enable"))
                else:
                    phase_y_enabled = bool(getattr(phase_y_cfg, "enable", False))
                if phase_y_enabled:
                    try:
                        from phaseY_self_opt import y_kernel, y_suggester, y_reporter  # type: ignore
                        # If optional module exists, use it.
                        fused = y_kernel.evaluate_run(RUN_SUMMARY if isinstance(RUN_SUMMARY, dict) else {})
                        suggestions = y_suggester.generate_suggestions(fused)
                        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        report_payload = {
                            "id": ts,
                            "timestamp": ts,
                            "run_id": RUN_SUMMARY.get("run_id", "") if isinstance(RUN_SUMMARY, dict) else "",
                            "analysis": fused,
                            "suggestions": suggestions,
                        }
                        y_reporter.write_phaseY_report(report_payload, base_dir=Path(".pipeline/phaseY/reports"))
                    except Exception:
                        # Fallback to existing self_heal implementations (informational only)
                        from phaseY_self_heal import heal_kernel, heal_classifier, heal_suggester, heal_reporter

                        kernel = heal_kernel.compute_heal_signals(RUN_SUMMARY if isinstance(RUN_SUMMARY, dict) else {})
                        classification = heal_classifier.classify(kernel)
                        suggestions = heal_suggester.suggest_corrections(
                            RUN_SUMMARY if isinstance(RUN_SUMMARY, dict) else {}, classification
                        )
                        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        report = {
                            "id": ts,
                            "timestamp": ts,
                            "run_id": RUN_SUMMARY.get("run_id", "") if isinstance(RUN_SUMMARY, dict) else "",
                            "kernel": kernel,
                            "classification": classification,
                            "suggestions": suggestions,
                            "overall_severity": kernel.get("signals", {}).get("severity", "low") if isinstance(kernel, dict) else "low",
                            "notes": "Phase Y self-heal report (informational only; no automatic actions).",
                        }
                        heal_reporter.write_heal_report(report, base_dir=Path(".pipeline/phaseY/reports"))
            except Exception:
                pass

            # Phase Z meta diagnostics (opt-in, read-only)
            try:
                phase_z_cfg = getattr(orchestrator_config, "phaseZ", None)
                if isinstance(phase_z_cfg, dict):
                    phase_z_enabled = bool(phase_z_cfg.get("enable"))
                else:
                    phase_z_enabled = bool(getattr(phase_z_cfg, "enable", False))
                if phase_z_enabled:
                    from phaseZ_meta import dependency_scanner, invariant_checker, meta_kernel, meta_reporter, phase_health_summarizer

                    kernel = meta_kernel.analyze_full_pipeline()
                    inv = invariant_checker.check_invariants(kernel)
                    deps = dependency_scanner.scan_dependencies()
                    health = phase_health_summarizer.summarize_health()
                    meta_reporter.write_meta_report(kernel, inv, deps, health, base_dir=Path(".pipeline/meta/reports"))
            except Exception:
                pass

            # Phase AC policy compiler (opt-in, read-only)
            try:
                phase_ac_cfg = getattr(orchestrator_config, "phaseAC", None)
                if isinstance(phase_ac_cfg, dict):
                    phase_ac_enabled = bool(phase_ac_cfg.get("enable"))
                else:
                    phase_ac_enabled = bool(getattr(phase_ac_cfg, "enable", False))
                if phase_ac_enabled:
                    from phaseAC_policy_compiler import compiler, merger, conflict_resolver, profile_writer

                    base_profile = compiler.compile_policy_profile(orchestrator_config, base_dir=Path(".pipeline"))
                    merged = merger.merge_policies([base_profile])
                    resolved = conflict_resolver.resolve_conflicts(merged)
                    profile_writer.write_policy_profile(resolved, base_dir=Path(".pipeline/policy_profiles"))
            except Exception:
                pass

            # Phase AD capability catalog (opt-in, read-only)
            try:
                phase_ad_cfg = getattr(orchestrator_config, "phaseAD", None)
                if isinstance(phase_ad_cfg, dict):
                    phase_ad_enabled = bool(phase_ad_cfg.get("enable"))
                else:
                    phase_ad_enabled = bool(getattr(phase_ad_cfg, "enable", False))
                if phase_ad_enabled:
                    from phaseAD_catalog import capability_scanner, catalog_builder, catalog_reporter

                    scanned = capability_scanner.scan_capabilities()
                    catalog = catalog_builder.build_catalog(scanned)
                    catalog_reporter.write_catalog(catalog, base_dir=Path(".pipeline/capability_catalog"))
            except Exception:
                pass

            # Phase AB Adaptive Brain (opt-in, read-only, no auto-apply)
            try:
                phase_ab_cfg = getattr(orchestrator_config, "phaseAB", None)
                if isinstance(phase_ab_cfg, dict):
                    phase_ab_enabled = bool(phase_ab_cfg.get("enable"))
                else:
                    phase_ab_enabled = bool(getattr(phase_ab_cfg, "enable", False))
                if phase_ab_enabled:
                    from uuid import uuid4
                    from phaseAB_adaptive import ab_kernel, ab_fusion, ab_classifier, ab_recommender, ab_reporter

                    raw_signals = ab_kernel.evaluate_all_sources(RUN_SUMMARY if isinstance(RUN_SUMMARY, dict) else {}, base_dir=".pipeline")
                    fused = ab_fusion.fuse_signals(raw_signals)
                    assessment = ab_classifier.classify_state(fused)
                    actions = ab_recommender.recommend_actions(fused, assessment)
                    report = {
                        "id": str(uuid4()),
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "signals": fused,
                        "unified_assessment": assessment,
                        "recommended_actions": actions,
                        "safe_to_apply": False,
                        "safety_envelope_version": "phaseAB_v1",
                    }
                    ab_reporter.write_ab_summary(report, base_dir=".pipeline/ab")
            except Exception:
                pass

            # Capabilities switchboard (read-only coordination for safe phases)
            try:
                capabilities_cfg = getattr(orchestrator_config, "capabilities", None)
                if isinstance(capabilities_cfg, dict):
                    cap_enabled = bool(capabilities_cfg.get("enable_safe_modes"))
                else:
                    cap_enabled = False
                if cap_enabled:
                    # This block is informational only; the individual phases already gate themselves.
                    capabilities_report = {
                        "capabilities": capabilities_cfg if isinstance(capabilities_cfg, dict) else {},
                        "notes": "Safe modes coordination (read-only).",
                    }
                    cap_dir = Path(".pipeline") / "capabilities" / "reports"
                    cap_dir.mkdir(parents=True, exist_ok=True)
                    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    cap_path = cap_dir / f"capabilities_{ts}.json"
                    cap_path.write_text(json.dumps(capabilities_report, indent=2), encoding="utf-8")
            except Exception:
                pass

            # Placeholder notices for phases A, B, C, AE, and AF (no implemented modules yet)
            try:
                phase_placeholders = [
                    ("phaseA", getattr(orchestrator_config, "phaseA", None)),
                    ("phaseB", getattr(orchestrator_config, "phaseB", None)),
                    ("phaseC", getattr(orchestrator_config, "phaseC", None)),
                    ("phaseAE", getattr(orchestrator_config, "phaseAE", None)),
                    ("phaseAF", getattr(orchestrator_config, "phaseAF", None)),
                ]
                for phase_name, cfg in phase_placeholders:
                    if isinstance(cfg, dict):
                        enabled = bool(cfg.get("enable"))
                    else:
                        enabled = bool(getattr(cfg, "enable", False))
                    if enabled:
                        logger.warning(
                            "%s is enabled in config but no orchestrator hook is registered; skipping.",
                            phase_name,
                        )
            except Exception:
                pass

    except Exception:
        logger.exception("Optional post-run phases failed")

    return 0


if __name__ == "__main__":
    sys.exit(main())
