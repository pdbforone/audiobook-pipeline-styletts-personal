from __future__ import annotations

from pathlib import Path

from dashboard.data import compute_dashboard_metrics, load_policy_events
from dashboard.plots import (
    plot_chunk_history,
    plot_engine_usage,
    plot_failure_table,
    plot_rtf_trend,
    plot_system_usage,
)

try:  # pragma: no cover - optional dependency
    import flet as ft
except Exception:  # pragma: no cover - fallback when Flet is missing
    ft = None  # type: ignore


def main(page: "ft.Page") -> None:
    if ft is None:
        raise RuntimeError("Flet is not installed. Install with `pip install flet` to launch the dashboard.")

    page.title = "Policy Engine Dashboard (Archived Flet UI)"
    page.scroll = "auto"

    events = load_policy_events()
    metrics = compute_dashboard_metrics(events)
    chart_paths = _build_charts(metrics)

    page.add(ft.Text("Policy Engine Dashboard", weight="bold", size=24))
    page.add(ft.Text(f"Loaded {len(events)} policy events."))

    for label, path in chart_paths.items():
        if not path:
            continue
        page.add(ft.Divider())
        page.add(ft.Text(label, size=18, weight="bold"))
        page.add(ft.Image(src=str(path), width=800))


def _build_charts(metrics):
    charts_dir = Path("policy_reports") / "charts"
    charts = {
        "RTF Trend": plot_rtf_trend(metrics.get("rtf_points") or [], charts_dir / "rtf_trend.png"),
        "Chunk Size History": plot_chunk_history(metrics.get("chunk_history") or [], charts_dir / "chunk_history.png"),
        "Engine Usage": plot_engine_usage(metrics.get("engine_counts") or {}, charts_dir / "engine_usage.png"),
        "Failure Reasons": plot_failure_table(metrics.get("failure_counts") or {}, charts_dir / "failures.png"),
        "CPU & Memory": plot_system_usage(metrics.get("system_points") or [], charts_dir / "system.png"),
    }
    return charts


if __name__ == "__main__":  # pragma: no cover - manual launch
    if ft is None:
        raise RuntimeError("Flet is not installed.")
    ft.app(target=main)
