"""
Enhanced Progress Display Components

Provides detailed, chunk-level progress tracking with modern UI
"""

from __future__ import annotations

from typing import Optional


def create_progress_html(
    phase: str,
    current_chunk: Optional[str],
    completed: int,
    total: int,
    failed: int = 0,
    current_operation: str = "",
    estimated_time: Optional[float] = None
) -> str:
    """
    Create enhanced progress bar HTML with detailed information.

    Args:
        phase: Phase name (e.g., "Phase 4", "Phase 5")
        current_chunk: Current chunk being processed (e.g., "chunk_0042")
        completed: Number of completed chunks
        total: Total number of chunks
        failed: Number of failed chunks
        current_operation: Current operation (e.g., "Synthesizing", "Enhancing")
        estimated_time: Estimated time remaining in seconds

    Returns:
        HTML string with styled progress bar
    """
    if total == 0:
        progress_percent = 0
    else:
        progress_percent = (completed / total) * 100

    # Format estimated time
    time_str = ""
    if estimated_time is not None:
        if estimated_time < 60:
            time_str = f"~{int(estimated_time)}s remaining"
        elif estimated_time < 3600:
            minutes = int(estimated_time / 60)
            time_str = f"~{minutes}m remaining"
        else:
            hours = int(estimated_time / 3600)
            minutes = int((estimated_time % 3600) / 60)
            time_str = f"~{hours}h {minutes}m remaining"

    # Create status text
    status_text = f"{current_operation} {current_chunk}" if current_chunk else f"{phase}"

    html = f"""
<div class="progress-container">
    <div class="progress-header">
        <span class="progress-title">{phase.upper()}</span>
        <span class="progress-stats">{completed}/{total} complete{' • ' + str(failed) + ' failed' if failed > 0 else ''}</span>
    </div>
    <div class="progress-bar-wrapper">
        <div class="progress-bar" style="width: {progress_percent:.1f}%"></div>
        <div class="progress-text">{progress_percent:.1f}% • {status_text}</div>
    </div>
    <div class="progress-details">
        <div class="progress-detail-line">
            <span class="progress-detail-label">Current Chunk:</span>
            <span class="progress-detail-value">{current_chunk or 'N/A'}</span>
        </div>
        <div class="progress-detail-line">
            <span class="progress-detail-label">Operation:</span>
            <span class="progress-detail-value">{current_operation or 'Idle'}</span>
        </div>
        {f'''<div class="progress-detail-line">
            <span class="progress-detail-label">Time Remaining:</span>
            <span class="progress-detail-value">{time_str}</span>
        </div>''' if time_str else ''}
        <div class="progress-detail-line">
            <span class="progress-detail-label">Success Rate:</span>
            <span class="progress-detail-value">{((completed - failed) / completed * 100 if completed > 0 else 0):.1f}%</span>
        </div>
    </div>
</div>
"""
    return html


def create_simple_progress_html(phase: str, progress_percent: float, status: str = "") -> str:
    """Create a simple progress bar without chunk details"""
    html = f"""
<div class="progress-container">
    <div class="progress-header">
        <span class="progress-title">{phase.upper()}</span>
        <span class="progress-stats">{status}</span>
    </div>
    <div class="progress-bar-wrapper">
        <div class="progress-bar" style="width: {progress_percent:.1f}%"></div>
        <div class="progress-text">{progress_percent:.1f}%</div>
    </div>
</div>
"""
    return html
