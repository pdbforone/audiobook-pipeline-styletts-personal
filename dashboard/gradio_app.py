import gradio as gr
import matplotlib.pyplot as plt
import json
import glob
from pathlib import Path

LOG_PATTERN = ".pipeline/policy_logs/*.log"
CHART_DIR = Path("dashboard_output") / "charts"
OVERRIDES_PATH = Path(".pipeline") / "tuning_overrides.json"


def _load_events():
    events = []
    for path_str in sorted(glob.glob(LOG_PATTERN)):
        path = Path(path_str)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def _phase_metrics():
    events = _load_events()
    phase_map = {}
    for event in events:
        phase = event.get("phase")
        if not phase:
            continue
        info = phase_map.setdefault(
            phase,
            {
                "phase": phase,
                "runs": 0,
                "success": 0,
                "failures": 0,
                "retries": 0,
                "duration_sum": 0.0,
                "duration_count": 0,
            },
        )
        event_type = event.get("event")
        if event_type in ("phase_end", "phase_failure"):
            info["runs"] += 1
            if event_type == "phase_end":
                info["success"] += 1
            else:
                info["failures"] += 1
            duration = event.get("duration_ms")
            if isinstance(duration, (int, float)):
                info["duration_sum"] += float(duration)
                info["duration_count"] += 1
        elif event_type == "phase_retry":
            info["retries"] += 1
    rows = []
    for phase in sorted(phase_map):
        info = phase_map[phase]
        avg = 0.0
        if info["duration_count"]:
            avg = (info["duration_sum"] / info["duration_count"]) / 1000.0
        rows.append(
            [
                phase,
                round(avg, 2),
                info["runs"],
                info["success"],
                info["failures"],
                info["retries"],
            ]
        )
    return rows, events


def _rtf_plot(events):
    samples = []
    for event in events:
        metrics = event.get("metrics") or {}
        value = metrics.get("avg_rt_factor")
        if isinstance(value, (int, float)):
            samples.append(float(value))
    if not samples:
        return None
    fig, ax = plt.subplots()
    ax.plot(range(1, len(samples) + 1), samples, marker="o")
    ax.set_title("Average RT Factor per Phase 4 run")
    ax.set_xlabel("Sample")
    ax.set_ylabel("RTF (x)")
    ax.grid(True, linestyle="--", alpha=0.4)
    return fig


def _engine_data():
    events = _load_events()
    counts = {}
    fallback_total = 0.0
    fallback_samples = 0
    cpu = []
    mem = []
    for event in events:
        metrics = event.get("metrics") or {}
        engine = metrics.get("selected_engine") or metrics.get("engine_used")
        if engine:
            counts[engine] = counts.get(engine, 0) + 1
        rate = metrics.get("fallback_rate")
        if isinstance(rate, (int, float)):
            fallback_total += float(rate)
            fallback_samples += 1
        cpu_value = event.get("cpu_percent")
        mem_value = event.get("memory_percent")
        if isinstance(cpu_value, (int, float)) and isinstance(
            mem_value, (int, float)
        ):
            cpu.append(float(cpu_value))
            mem.append(float(mem_value))
    rows = [
        [engine, counts[engine]]
        for engine in sorted(counts, key=counts.get, reverse=True)
    ]
    fallback_avg = ""
    if fallback_samples:
        fallback_avg = f"Average fallback rate: {round((fallback_total / fallback_samples) * 100, 2)}%"
    else:
        fallback_avg = "Average fallback rate: n/a"
    fig = None
    if cpu and mem:
        fig, ax = plt.subplots()
        ax.plot(range(len(cpu)), cpu, label="CPU %", linewidth=1.2)
        ax.plot(range(len(mem)), mem, label="Memory %", linewidth=1.2)
        ax.set_xlabel("Sample")
        ax.set_ylabel("Percent")
        ax.set_title("System Utilization")
        ax.set_ylim(0, 100)
        ax.legend()
        ax.grid(True, linestyle="--", alpha=0.4)
    return rows, fallback_avg, fig


def _chunk_error_stats():
    events = _load_events()
    chunk_failures = 0
    hallucinations = 0
    failure_reasons = {}
    for event in events:
        errors = event.get("errors") or []
        message = " ".join(str(err) for err in errors)
        if "chunk" in message.lower():
            chunk_failures += 1
        if "hallucination" in message.lower():
            hallucinations += 1
        if errors and event.get("event") == "phase_failure":
            reason = errors[0]
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    summary = (
        f"Chunk-related errors: {chunk_failures} | "
        f"Hallucination indicators: {hallucinations} | "
        f"Recorded failure reasons: {len(failure_reasons)}"
    )
    return summary


def _load_overrides_text():
    if not OVERRIDES_PATH.exists():
        return "No overrides file found."
    try:
        data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "Overrides file is not valid JSON."
    return json.dumps(data, indent=2, ensure_ascii=False)


def _chart_image(name):
    path = CHART_DIR / name
    if path.exists():
        return str(path), ""
    return (
        None,
        f"{name} not found. Run `python -m dashboard.report` to generate charts.",
    )


def _phase_choices():
    phases = ["(all phases)"]
    events = _load_events()
    seen = []
    for event in events:
        phase = event.get("phase")
        if phase and phase not in seen:
            seen.append(phase)
    return phases + seen


PHASE_CHOICES = _phase_choices()


def refresh_phase_tab():
    rows, events = _phase_metrics()
    rtf_fig = _rtf_plot(events)
    img, msg = _chart_image("rtf_trend.png")
    return rows, rtf_fig, img, (msg or "Saved chart loaded.")


def refresh_engine_tab():
    rows, fallback_text, cpu_plot = _engine_data()
    img, msg = _chart_image("system.png")
    return rows, fallback_text, cpu_plot, img, (msg or "System chart loaded.")


def refresh_chunk_tab():
    summary = _chunk_error_stats()
    chunk_img, chunk_msg = _chart_image("chunk_history.png")
    failure_img, failure_msg = _chart_image("failures.png")
    return (
        summary,
        chunk_img,
        (chunk_msg or "Chunk history chart loaded."),
        failure_img,
        (failure_msg or "Failure chart loaded."),
    )


def refresh_overrides():
    return _load_overrides_text()


def refresh_logs(phase, query, limit):
    try:
        limit_value = int(limit)
    except Exception:
        limit_value = 20
    limit_value = max(1, min(limit_value, 200))
    events = _load_events()
    query_norm = (query or "").strip().lower()
    selected = [] if phase == "(all phases)" else phase
    lines = []
    count = 0
    for event in reversed(events):
        if selected and event.get("phase") != selected:
            continue
        text = json.dumps(event, ensure_ascii=False)
        if query_norm and query_norm not in text.lower():
            continue
        lines.append(text)
        count += 1
        if count >= limit_value:
            break
    if not lines:
        return "No log entries found."
    return "\n\n".join(lines)


with gr.Blocks() as demo:
    gr.Markdown(
        "# Self-Tuning Gradio Dashboard\n"
        "Visualize policy metrics, overrides, and logs. This dashboard is optional and does not impact runtime."
    )

    with gr.Tab("Phase Metrics"):
        phase_button = gr.Button("Refresh Phase Metrics")
        phase_table = gr.Dataframe(
            headers=[
                "Phase",
                "Avg Duration (s)",
                "Runs",
                "Success",
                "Failures",
                "Retries",
            ],
            datatype=["str", "number", "number", "number", "number", "number"],
            interactive=False,
        )
        rtf_plot = gr.Plot(label="RTF Trend")
        phase_image = gr.Image(label="Saved Chart: rtf_trend.png")
        phase_message = gr.Markdown()
        phase_button.click(
            refresh_phase_tab,
            outputs=[phase_table, rtf_plot, phase_image, phase_message],
        )
        demo.load(
            refresh_phase_tab,
            outputs=[phase_table, rtf_plot, phase_image, phase_message],
        )

    with gr.Tab("Engines & Load"):
        engine_button = gr.Button("Refresh Engine Stats")
        engine_table = gr.Dataframe(
            headers=["Engine", "Occurrences"],
            datatype=["str", "number"],
            interactive=False,
        )
        fallback_text = gr.Markdown()
        cpu_plot = gr.Plot(label="CPU / Memory Trend")
        system_image = gr.Image(label="Saved Chart: system.png")
        system_message = gr.Markdown()
        engine_button.click(
            refresh_engine_tab,
            outputs=[
                engine_table,
                fallback_text,
                cpu_plot,
                system_image,
                system_message,
            ],
        )
        demo.load(
            refresh_engine_tab,
            outputs=[
                engine_table,
                fallback_text,
                cpu_plot,
                system_image,
                system_message,
            ],
        )

    with gr.Tab("Chunk & Error History"):
        chunk_button = gr.Button("Refresh Error Snapshot")
        chunk_summary = gr.Markdown()
        chunk_image = gr.Image(label="Saved Chart: chunk_history.png")
        chunk_msg = gr.Markdown()
        failure_image = gr.Image(label="Saved Chart: failures.png")
        failure_msg = gr.Markdown()
        chunk_button.click(
            refresh_chunk_tab,
            outputs=[
                chunk_summary,
                chunk_image,
                chunk_msg,
                failure_image,
                failure_msg,
            ],
        )
        demo.load(
            refresh_chunk_tab,
            outputs=[
                chunk_summary,
                chunk_image,
                chunk_msg,
                failure_image,
                failure_msg,
            ],
        )

    with gr.Tab("Overrides"):
        override_button = gr.Button("Refresh Overrides")
        override_text = gr.Textbox(
            label="Current tuning_overrides.json", lines=20
        )
        override_button.click(refresh_overrides, outputs=override_text)
        demo.load(refresh_overrides, outputs=override_text)

    with gr.Tab("Logs Viewer"):
        with gr.Row():
            phase_dropdown = gr.Dropdown(
                choices=PHASE_CHOICES,
                value=PHASE_CHOICES[0],
                label="Phase",
            )
            query_box = gr.Textbox(label="Search text (optional)")
            limit_box = gr.Number(value=20, label="Max entries")
        logs_button = gr.Button("Fetch Logs")
        logs_output = gr.Textbox(label="Log Output", lines=20)
        logs_button.click(
            refresh_logs,
            inputs=[phase_dropdown, query_box, limit_box],
            outputs=logs_output,
        )


def main():
    demo.launch()


if __name__ == "__main__":
    main()
