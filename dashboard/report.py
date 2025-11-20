from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .data import compute_dashboard_metrics, load_policy_events
from .plots import (
    plot_chunk_history,
    plot_engine_usage,
    plot_failure_table,
    plot_rtf_trend,
    plot_system_usage,
)


def build_weekly_report(output_path: Path) -> Path:
    events = load_policy_events()
    metrics = compute_dashboard_metrics(events)
    charts_dir = output_path.parent / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)

    chart_paths = {
        "RTF Trend": plot_rtf_trend(metrics.get("rtf_points") or [], charts_dir / "rtf_trend.png"),
        "Chunk Size History": plot_chunk_history(metrics.get("chunk_history") or [], charts_dir / "chunk_history.png"),
        "Engine Usage": plot_engine_usage(metrics.get("engine_counts") or {}, charts_dir / "engine_usage.png"),
        "Failure Reasons": plot_failure_table(metrics.get("failure_counts") or {}, charts_dir / "failures.png"),
        "CPU & Memory": plot_system_usage(metrics.get("system_points") or [], charts_dir / "system.png"),
    }

    lines = [
        "# Weekly Policy Report",
        "",
        f"_Generated {datetime.utcnow().isoformat(timespec='seconds')}Z_",
        "",
        f"- Total policy events analyzed: **{len(events)}**",
        f"- Unique engines recorded: **{len(metrics.get('engine_counts') or {})}**",
        f"- Failure reasons logged: **{len(metrics.get('failure_counts') or {})}**",
        "",
    ]

    lines.extend(_chart_section("RTF Trend", chart_paths["RTF Trend"]))
    lines.extend(_chart_section("Chunk Size History", chart_paths["Chunk Size History"]))
    lines.extend(_chart_section("Engine Usage", chart_paths["Engine Usage"]))
    lines.extend(_chart_section("Failure Reasons", chart_paths["Failure Reasons"]))
    lines.extend(_chart_section("CPU & Memory", chart_paths["CPU & Memory"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _chart_section(title: str, chart_path: Optional[Path]) -> List[str]:
    if not chart_path:
        return [f"## {title}", "", "_No data available._", ""]
    rel_path = chart_path.as_posix()
    return [f"## {title}", "", f"![{title}]({rel_path})", ""]


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the weekly policy report.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("policy_reports/weekly.md"),
        help="Destination markdown file (default: policy_reports/weekly.md)",
    )
    args = parser.parse_args(argv)
    build_weekly_report(args.output)
    print(f"Weekly report written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
