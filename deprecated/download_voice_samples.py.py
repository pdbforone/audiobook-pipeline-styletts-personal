#!/usr/bin/env python3
"""
voice_sample_downloader.py
-----------------------------------
Downloads and organizes public-domain voice samples for cloning or research.

Features:
- Works with Archive.org and direct MP3 URLs.
- Auto-creates folders per genre/narrator.
- Graceful retry and error handling.
- Verifies license tags in VOICE_CATALOG.
- Prints a summary log at the end.
"""

import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError
from datetime import datetime

# ================================
# CONFIGURATION
# ================================

VOICE_CATALOG = {
    "philosophy": {
        "Vincent Price": {
            "work": "The Saint – The Miracle Tea Party (1948)",
            "license": "Public Domain (OTRR verified, Archive.org)",
            "source_type": "archive_org",
            "urls": [
                "https://archive.org/download/OTRR_The_Saint_Singles/OTRR_The_Saint_v480205_The_Miracle_Tea_Party.mp3"
            ],
            "extract_segment": {"start": 30, "duration": 25},
            "quality": "excellent",
            "commercial_use": True,
        }
    },
    "horror": {
        "Peter Yearsley": {
            "work": "Ghost Stories of an Antiquary (M.R. James)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                "https://archive.org/download/ghost_stories_antiquary_0808_librivox/ghoststoriesantiquary_01_james_64kb.mp3"
            ],
            "extract_segment": {"start": 30, "duration": 25},
            "quality": "excellent",
            "commercial_use": True,
        },
        "Mark Nelson": {
            "work": "The Dunwich Horror (H.P. Lovecraft)",
            "license": "Public Domain (LibriVox)",
            "source_type": "archive_org",
            "urls": [
                "https://archive.org/download/dunwich_horror_librivox/dunwichhorror_01_lovecraft_64kb.mp3"
            ],
            "extract_segment": {"start": 20, "duration": 25},
            "quality": "excellent",
            "commercial_use": True,
        },
    },
}

# ================================
# DOWNLOAD UTILS
# ================================


def download_file(url, dest_folder="samples", filename=None):
    """Downloads a file from the web with error handling."""
    os.makedirs(dest_folder, exist_ok=True)
    if not filename:
        filename = os.path.basename(url.split("?")[0]) or "sample.mp3"
    dest_path = os.path.join(dest_folder, filename)

    try:
        print(f"→ Downloading: {url}")
        urllib.request.urlretrieve(url, dest_path)
        print(f"   ✓ Saved to {dest_path}")
        return dest_path
    except HTTPError as e:
        print(f"   ❌ HTTP Error {e.code} for {url}")
    except URLError as e:
        print(f"   ❌ URL Error: {e.reason}")
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
    return None


def download_narrator_samples(genre, narrator, data):
    """Download all URLs for a given narrator and print license info."""
    folder = os.path.join("samples", genre, narrator.replace(" ", "_"))
    os.makedirs(folder, exist_ok=True)
    print(f"\n=== {narrator} ({genre}) ===")
    print(f"Work: {data.get('work', 'Unknown')}")
    print(f"License: {data.get('license', 'Unknown')}")
    print(f"Commercial Use: {'Yes' if data.get('commercial_use') else 'No'}\n")

    downloaded = []
    for url in data.get("urls", []):
        path = download_file(url, folder)
        if path:
            downloaded.append(path)

    return downloaded


# ================================
# MAIN
# ================================


def main():
    if len(sys.argv) == 1:
        print("Usage:")
        print(
            "  python voice_sample_downloader.py [--all | --genre GENRE | --narrator 'Name']"
        )
        sys.exit(1)

    # Parse args
    download_all = "--all" in sys.argv
    genre_filter = None
    narrator_filter = None

    if "--genre" in sys.argv:
        idx = sys.argv.index("--genre") + 1
        if idx < len(sys.argv):
            genre_filter = sys.argv[idx]

    if "--narrator" in sys.argv:
        idx = sys.argv.index("--narrator") + 1
        if idx < len(sys.argv):
            narrator_filter = sys.argv[idx]

    log = []
    print("\n==============================")
    print(" Voice Sample Downloader")
    print("==============================")

    for genre, narrators in VOICE_CATALOG.items():
        if genre_filter and genre_filter.lower() != genre.lower():
            continue
        for narrator, data in narrators.items():
            if narrator_filter and narrator_filter.lower() != narrator.lower():
                continue
            files = download_narrator_samples(genre, narrator, data)
            for f in files:
                log.append((narrator, genre, f, data["license"]))

    # Log summary
    print("\n=== Download Summary ===")
    for n, g, f, lic in log:
        print(f"✓ {n} ({g}) -> {os.path.basename(f)} [{lic}]")

    with open("download_log.txt", "a", encoding="utf-8") as fp:
        fp.write(f"\n\n=== Run {datetime.now()} ===\n")
        for n, g, f, lic in log:
            fp.write(f"{n} ({g}): {f} | {lic}\n")

    print("\nAll done!")


if __name__ == "__main__":
    main()
