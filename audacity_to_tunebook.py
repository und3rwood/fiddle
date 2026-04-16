#!/usr/bin/env python3
"""
audacity_to_tunebook.py
-----------------------
Reads Audacity label .txt files from your tunes/ directory and
writes (or updates) tunebook.json.

Usage:
    python3 audacity_to_tunebook.py

Directory layout expected:
    tunes/
      cliffs-of-moher/
        audio.mp3          ← your exported audio
        labels.txt         ← exported from Audacity: File > Export > Export Labels
      galway-rambler/
        audio.mp3
        labels.txt

Audacity label format (tab-separated):
    0.000000    28.430000    A part - first time
    28.430000   56.100000    A part - second time
    ...

If a tune already exists in tunebook.json its sections are updated
but title/tags/speedOptions you've edited manually are preserved.

Run this from the root of your tunebook folder (next to index.html).
"""

import json
import os
import re
import sys
from pathlib import Path


TUNES_DIR   = Path("tunes")
OUTPUT_FILE = Path("tunebook.json")


def parse_labels(path: Path) -> list[dict]:
    """Parse an Audacity labels .txt file into section dicts."""
    sections = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                # point label (single timestamp) — skip
                continue
            try:
                start = float(parts[0])
                end   = float(parts[1])
                label = parts[2].strip()
            except ValueError:
                continue
            sections.append({"label": label, "start": round(start, 3), "end": round(end, 3)})
    return sections


def slug_to_title(slug: str) -> str:
    """Convert a directory slug like 'cliffs-of-moher' to 'Cliffs of Moher'."""
    stop_words = {"of", "the", "a", "an", "and", "in", "on", "at", "to", "for"}
    words = slug.replace("-", " ").replace("_", " ").split()
    titled = []
    for i, w in enumerate(words):
        titled.append(w.capitalize() if (i == 0 or w not in stop_words) else w)
    return " ".join(titled)


def find_audio(tune_dir: Path) -> str | None:
    for ext in ["mp3", "ogg", "wav", "m4a", "flac"]:
        f = tune_dir / f"audio.{ext}"
        if f.exists():
            return f"tunes/{tune_dir.name}/audio.{ext}"
    return None


def main():
    if not TUNES_DIR.exists():
        sys.exit(f"Error: '{TUNES_DIR}' directory not found. Run from your tunebook root.")

    # load existing tunebook.json if present
    existing: dict[str, dict] = {}
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, encoding="utf-8") as f:
            try:
                for entry in json.load(f):
                    # key by audioSrc so we can match back to directory
                    existing[entry.get("audioSrc", "")] = entry
            except json.JSONDecodeError:
                print("Warning: existing tunebook.json was malformed — will overwrite.")

    entries = []
    tune_dirs = sorted(
        [d for d in TUNES_DIR.iterdir() if d.is_dir()],
        key=lambda d: d.name
    )

    if not tune_dirs:
        sys.exit(f"No subdirectories found in '{TUNES_DIR}'. Add a folder per tune.")

    for tune_dir in tune_dirs:
        labels_path = tune_dir / "labels.txt"
        if not labels_path.exists():
            print(f"  skipping {tune_dir.name}/ — no labels.txt found")
            continue

        audio_src = find_audio(tune_dir)
        if not audio_src:
            print(f"  skipping {tune_dir.name}/ — no audio file found")
            continue

        sections = parse_labels(labels_path)
        print(f"  {tune_dir.name}: {len(sections)} section(s)")

        # preserve any manually-edited fields from the existing entry
        old = existing.get(audio_src, {})
        entry = {
            "title":        old.get("title", slug_to_title(tune_dir.name)),
            "tags":         old.get("tags", []),
            "audioSrc":     audio_src,
            "speedOptions": old.get("speedOptions", [0.5, 0.75, 1.0]),
            "sections":     sections,
        }
        entries.append(entry)

    if not entries:
        sys.exit("No tunes processed. Check your tunes/ subdirectories.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(entries)} tune(s) to {OUTPUT_FILE}")
    print("Open index.html in a browser (via a local server) to preview.")


if __name__ == "__main__":
    main()
