from __future__ import annotations

import argparse
import difflib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from policy_engine import PolicyAdvisor
from policy_engine.policy_engine import OVERRIDES_PATH
SOURCE_LABEL = "policy_engine_cli"


@dataclass
class Candidate:
    path: Tuple[str, ...]
    title: str
    value: Dict[str, Any]
    reason: str


def load_overrides(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle) or {}
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}
    return {
        "version": int(data.get("version", 1)),
        "updated": data.get("updated"),
        "overrides": data.get("overrides", {}),
        "history": data.get("history", []),
    }


def save_overrides(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


def format_diff(existing: Optional[Dict[str, Any]], proposed: Dict[str, Any]) -> str:
    current_lines = (
        json.dumps(existing, indent=2, sort_keys=True).splitlines()
        if existing
        else ["<none>"]
    )
    proposed_lines = json.dumps(proposed, indent=2, sort_keys=True).splitlines()
    if existing == proposed:
        return "No change (already applied)."
    diff = list(
        difflib.unified_diff(
            current_lines, proposed_lines, fromfile="current", tofile="proposed", lineterm=""
        )
    )
    if not diff:
        return "\n".join(proposed_lines)
    return "\n".join(diff)


def get_nested(data: Dict[str, Any], path: Sequence[str]) -> Optional[Dict[str, Any]]:
    cursor: Any = data
    for key in path:
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor if isinstance(cursor, dict) else None


def set_nested(data: Dict[str, Any], path: Sequence[str], value: Dict[str, Any]) -> None:
    cursor = data
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value


def build_candidates(advisor: PolicyAdvisor, file_label: str) -> List[Candidate]:
    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    candidates: List[Candidate] = []

    phase3_advice = advisor.advise({"phase": "phase3", "file_id": file_label})
    chunk_size = phase3_advice.get("chunk_size")
    if chunk_size:
        candidates.append(
            Candidate(
                path=("phase3", "chunk_size"),
                title="Phase 3 chunk sizing",
                reason=chunk_size.get("reason", "Adjust chunk size"),
                value={
                    "mode": chunk_size.get("action"),
                    "reason": chunk_size.get("reason"),
                    "confidence": chunk_size.get("confidence"),
                    "delta_percent": chunk_size.get("delta_percent", 15),
                    "source": SOURCE_LABEL,
                    "updated_at": timestamp,
                },
            )
        )

    retry_overrides: Dict[str, Dict[str, Any]] = {}
    for phase in ("phase4", "phase5", "phase5.5"):
        advice = advisor.advise({"phase": phase, "file_id": file_label})
        engine = advice.get("engine")
        if phase == "phase4" and engine:
            candidates.append(
                Candidate(
                    path=("phase4", "engine"),
                    title="Phase 4 engine preference",
                    reason=engine.get("reason", ""),
                    value={
                        "preferred": engine.get("engine"),
                        "confidence": engine.get("confidence"),
                        "reason": engine.get("reason"),
                        "source": SOURCE_LABEL,
                        "updated_at": timestamp,
                    },
                )
            )
        voice = advice.get("voice_variant")
        if phase == "phase4" and voice:
            candidates.append(
                Candidate(
                    path=("phase4", "voice_variant"),
                    title="Phase 4 voice variant",
                    reason=voice.get("reason", ""),
                    value={
                        "action": voice.get("action"),
                        "reason": voice.get("reason"),
                        "voice_id": voice.get("voice_id"),
                        "source": SOURCE_LABEL,
                        "updated_at": timestamp,
                    },
                )
            )
        retry = advice.get("retry_policy")
        if retry:
            retry_phase = retry.get("phase") or phase
            retry_overrides[retry_phase] = {
                "suggested_retries": retry.get("suggested_retries"),
                "reason": retry.get("reason"),
                "source": SOURCE_LABEL,
                "updated_at": timestamp,
            }

    for phase_name, payload in retry_overrides.items():
        candidates.append(
            Candidate(
                path=(phase_name, "retry_policy"),
                title=f"{phase_name} retry policy",
                reason=payload.get("reason", ""),
                value=payload,
            )
        )

    return candidates


def prompt_apply(candidate: Candidate, diff_text: str) -> bool:
    print(f"\n[{candidate.title}]")
    print(f"Reason: {candidate.reason}")
    print(f"Override path: {'.'.join(candidate.path)}")
    print(diff_text)
    while True:
        try:
            response = input("Apply this override? [y/N]: ").strip().lower()
        except EOFError:
            return False
        if not response:
            return False
        if response in {"y", "yes"}:
            return True
        if response in {"n", "no"}:
            return False
        print("Please answer 'y' or 'n'.")


def tune_command(args: argparse.Namespace) -> int:
    pipeline_path = Path(args.pipeline).resolve()
    if not pipeline_path.exists():
        print(f"Pipeline file not found: {pipeline_path}")
        return 1

    file_label = args.label or pipeline_path.stem
    advisor = PolicyAdvisor()
    candidates = build_candidates(advisor, file_label)
    if not candidates:
        print("No policy suggestions available right now.")
        return 0

    overrides = load_overrides(OVERRIDES_PATH)
    accepted: List[Dict[str, Any]] = []
    for candidate in candidates:
        existing = get_nested(overrides["overrides"], candidate.path)
        if existing == candidate.value:
            continue
        if candidate.path[-1] == "voice_variant" and not candidate.value.get("voice_id"):
            if args.yes:
                print("Skipping voice override because no voice ID was provided.")
                continue
            voice_choice = input("Enter voice ID to apply (leave blank to skip): ").strip()
            if not voice_choice:
                print("Skipping voice override.")
                continue
            candidate.value["voice_id"] = voice_choice
        diff_text = format_diff(existing, candidate.value)
        apply_change = args.yes or prompt_apply(candidate, diff_text)
        if not apply_change:
            continue
        set_nested(overrides["overrides"], candidate.path, candidate.value)
        accepted.append(
            {
                "path": ".".join(candidate.path),
                "reason": candidate.reason,
                "value": candidate.value,
            }
        )

    if not accepted:
        print("No overrides were applied.")
        return 0

    timestamp = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    overrides["updated"] = timestamp
    history_entry = {
        "timestamp": timestamp,
        "pipeline": str(pipeline_path),
        "changes": accepted,
    }
    overrides.setdefault("history", []).append(history_entry)
    save_overrides(OVERRIDES_PATH, overrides)
    print(f"Overrides updated: {OVERRIDES_PATH}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Human-approved tuning CLI.")
    sub = parser.add_subparsers(dest="command")

    tune = sub.add_parser("tune", help="Review and apply policy suggestions.")
    tune.add_argument(
        "--pipeline",
        type=str,
        default="pipeline.json",
        help="Pipeline JSON file (used for labeling only).",
    )
    tune.add_argument(
        "--label",
        type=str,
        default=None,
        help="Optional friendly label for the affected file_id.",
    )
    tune.add_argument(
        "--yes",
        action="store_true",
        help="Apply all suggestions without prompting.",
    )
    tune.set_defaults(func=tune_command)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
