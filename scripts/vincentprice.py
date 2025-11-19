from pathlib import Path

from pydub import AudioSegment

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICES_DIR = PROJECT_ROOT / "Voices"
FILES = {
    VOICES_DIR
    / "Agnes_Moorehead"
    / "Suspense%20490127%20325%20The%20Thing%20in%20the%20Window%20(128-44)%2028267%2029m28s.mp3": 2 * 60 + 39,
    VOICES_DIR / "Vincent_Price" / "500317_Escape_Three_Skeleton_Key.mp3": 1 * 60 + 5,
    VOICES_DIR / "Vincent_Price" / "Escape_470530_Blood_Bath.mp3": 1 * 60 + 59,
    VOICES_DIR
    / "Vincent_Price"
    / "Suspense%20471128%20273%20The%20Pit%20and%20the%20Pendulum%20(64-44)%2014324%2029m52s.mp3": 20 * 60 + 34,
    VOICES_DIR
    / "Mercedes_McCambridge"
    / "Suspense%20481209%20318%20The%20Sisters%20(128-44)%2028551%2029m46s.mp3": 14 * 60 + 16,
}

TRIM_DURATION = 30 * 1000  # 30 seconds in ms

for path, start_time in FILES.items():
    try:
        print(f"?? Processing {path.name} from {start_time}s")
        audio = AudioSegment.from_file(str(path))
        end_time = (start_time * 1000) + TRIM_DURATION
        trimmed = audio[start_time * 1000 : end_time]

        output_path = path.with_name(f"{path.stem}_sample30s.mp3")
        trimmed.export(str(output_path), format="mp3")
        print(f"? Saved 30s sample: {output_path}")
    except Exception as e:
        print(f"? Error processing {path}: {e}")
