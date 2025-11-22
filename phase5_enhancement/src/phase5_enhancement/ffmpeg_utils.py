import os
import tempfile
import datetime
from pathlib import Path
import subprocess
import logging

logger = logging.getLogger(__name__)


def run_ffmpeg(cmd: list[str], desc: str) -> None:
    """Run an ffmpeg-like command and raise on failure.

    This utility is intentionally standalone and only uses the standard
    library so it can be imported without heavy scientific/audio deps.
    On failure it writes a timestamped diagnostics log under
    `<repo-root>/phase5_enhancement/logs/` (or falls back to temp/CWD)
    and raises a RuntimeError including the diagnostics path.
    """
    # Run command and capture output
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        return

    # Determine repo-root-like base for logs
    try:
        # If caller set REPO_ROOT globally, prefer that
        if "REPO_ROOT" in globals():
            pkg_root = globals().get("REPO_ROOT")
            if isinstance(pkg_root, (str, Path)):
                pkg_root = Path(pkg_root)
        else:
            pkg_root = Path(__file__).resolve().parents[3]
    except Exception:
        pkg_root = Path.cwd()

    primary_logs_dir = pkg_root / "phase5_enhancement" / "logs"
    fallback_dirs = [Path(tempfile.gettempdir()), Path.cwd()]

    try:
        primary_logs_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = primary_logs_dir
    except Exception:
        logs_dir = None

    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    pid = os.getpid()
    safe_desc = str(desc).replace(" ", "_").replace("/", "_")
    log_name = f"ffmpeg_failure_{safe_desc}_{timestamp}_{pid}.log"

    stderr_text = result.stderr or ""
    stdout_text = result.stdout or ""
    stderr_lines = stderr_text.splitlines()
    stderr_preview = "\n".join(stderr_lines[:200])
    stdout_preview = "\n".join(stdout_text.splitlines()[:50])
    # Shorter preview for error messages to avoid extremely long lines
    stderr_preview_short = stderr_preview[:1000]

    write_contents = (
        f"FFmpeg command: {' '.join(cmd)}\n"
        f"Exit code: {result.returncode}\n"
        "\n--- STDOUT (preview) ---\n"
        f"{stdout_preview}\n"
        "\n--- STDERR (preview) ---\n"
        f"{stderr_preview}\n"
    )

    try_locations = []
    if primary_logs_dir is not None:
        try_locations.append(primary_logs_dir)
    if logs_dir is not None and logs_dir not in try_locations:
        try_locations.append(logs_dir)
    try_locations.extend(fallback_dirs)

    log_path = None
    for base in try_locations:
        try:
            base.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        candidate = base / log_name
        try:
            with open(candidate, "w", encoding="utf-8") as fh:
                fh.write(write_contents)
                if len(stderr_lines) > 200:
                    truncated_note = "\n... (stderr truncated, total lines=" + str(len(stderr_lines)) + ")\n"
                    fh.write(truncated_note)
            log_path = candidate
            break
        except Exception:
            continue

    if log_path is None:
        try:
            candidate = Path(tempfile.gettempdir()) / log_name
            with open(candidate, "w", encoding="utf-8") as fh:
                fh.write(write_contents)
            log_path = candidate
        except Exception:
            msg = (
                "FFmpeg "
                + str(desc)
                + " failed (exit "
                + str(result.returncode)
                + "). Could not write diagnostics log. stderr preview:\n"
                + stderr_preview_short
            )
            raise RuntimeError(msg)

    try:
        logger.error(
            "FFmpeg %s failed (exit %s). Diagnostics written to: %s",
            desc,
            result.returncode,
            str(log_path),
        )
        logger.error("FFmpeg stderr (preview): %s", stderr_preview_short)
    except Exception:
        pass

    msg = (
        "FFmpeg "
        + str(desc)
        + " failed (exit "
        + str(result.returncode)
        + "). See ffmpeg diagnostics: "
        + str(log_path)
        + " \nstderr preview:\n"
        + stderr_preview_short
    )
    raise RuntimeError(msg)
