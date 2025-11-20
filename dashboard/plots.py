from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def plot_rtf_trend(points: Sequence[Tuple[float, float]], output_path: Path) -> Optional[Path]:
    if not points:
        return None
    times, values = zip(*points)
    fig, ax = _new_figure()
    ax.plot(times, values, marker="o", linewidth=1.5)
    ax.set_title("Average RTF per Phase 4 run")
    ax.set_ylabel("RTF (x)")
    ax.set_xlabel("Timestamp")
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=45)
    return _save(fig, output_path)


def plot_chunk_history(history: Sequence[Dict[str, float]], output_path: Path) -> Optional[Path]:
    if not history:
        return None
    indices = list(range(len(history)))
    deltas = [float(item.get("delta_percent") or 0.0) for item in history]
    labels = [item.get("label") or "" for item in history]
    fig, ax = _new_figure()
    ax.bar(indices, deltas, color="#4c78a8")
    ax.set_title("Chunk Size Delta History")
    ax.set_ylabel("Delta (%)")
    ax.set_xticks(indices, labels, rotation=45, ha="right")
    ax.axhline(0, color="black", linewidth=0.8)
    return _save(fig, output_path)


def plot_engine_usage(engine_counts: Dict[str, int], output_path: Path) -> Optional[Path]:
    if not engine_counts:
        return None
    labels = list(engine_counts.keys())
    values = [engine_counts[label] for label in labels]
    fig, ax = _new_figure()
    ax.bar(labels, values, color="#e45756")
    ax.set_ylabel("Phase 4 Completions")
    ax.set_title("Engine Usage")
    return _save(fig, output_path)


def plot_failure_table(failure_counts: Dict[str, int], output_path: Path) -> Optional[Path]:
    if not failure_counts:
        return None
    rows = sorted(failure_counts.items(), key=lambda item: item[1], reverse=True)
    fig, ax = _new_figure(figsize=(8, max(1, 0.4 * len(rows) + 1)))
    ax.axis("off")
    table = ax.table(
        cellText=[[reason, count] for reason, count in rows],
        colLabels=["Reason", "Occurrences"],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.2)
    ax.set_title("Failure Reasons")
    return _save(fig, output_path)


def plot_system_usage(points: Sequence[Tuple[float, float, float]], output_path: Path) -> Optional[Path]:
    if not points:
        return None
    times = [p[0] for p in points]
    cpu = [p[1] for p in points]
    memory = [p[2] for p in points]
    fig, ax = _new_figure()
    ax.plot(times, cpu, label="CPU %", linewidth=1.5)
    ax.plot(times, memory, label="Memory %", linewidth=1.2)
    ax.set_ylim(0, 100)
    ax.set_title("Host Utilization (from policy logs)")
    ax.set_ylabel("Percent")
    ax.set_xlabel("Timestamp")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=45)
    return _save(fig, output_path)


def _new_figure(figsize: Tuple[float, float] = (8, 4)) -> Tuple[Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=figsize)
    fig.tight_layout()
    return fig, ax


def _save(fig: Figure, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path
