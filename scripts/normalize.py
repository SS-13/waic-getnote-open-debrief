"""Normalize raw notes in 1-data/<year>/ into 2-processing/<year>/notes.csv.

Single-file design. Reads .md files written by scripts/fetch.py, extracts
frontmatter + transcript, writes a flat CSV.

Usage:
    python scripts/normalize.py --year 2025
"""

from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

from scripts.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("normalize")


_FRONTMATTER_RE = re.compile(r"^---\s*$", re.MULTILINE)


def parse_note(md_path: Path) -> dict | None:
    """Parse a markdown note written by scripts/fetch.py."""
    text = md_path.read_text(encoding="utf-8")
    parts = _FRONTMATTER_RE.split(text, maxsplit=2)
    if len(parts) < 3:
        log.warning("skip malformed file (no frontmatter): %s", md_path)
        return None

    front = parts[1].strip()
    body = parts[2]

    rec: dict = {"source_path": str(md_path.relative_to(settings.repo_root))}
    for line in front.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip().lstrip("-").strip()
        val = val.strip()
        rec[key] = val

    # Body -> transcript
    transcript = ""
    if "## Transcript" in body:
        transcript = body.split("## Transcript", 1)[1].strip()
    rec["transcript_len"] = len(transcript)

    # Date / year / id
    if "date" in rec:
        rec["date"] = rec["date"]
        rec["year"] = rec["date"][:4] if rec["date"] else ""
    rec["note_id"] = rec.get("note_id") or md_path.stem

    return rec


def run(year: int) -> int:
    src_dir = settings.repo_root / "1-data" / str(year)
    if not src_dir.exists():
        log.error("source dir not found: %s", src_dir)
        return 0

    out_dir = settings.repo_root / "2-processing" / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "notes.csv"

    rows: list[dict] = []
    for md in sorted(src_dir.glob("*.md")):
        rec = parse_note(md)
        if rec is None:
            continue
        rows.append(rec)

    if not rows:
        log.warning("no notes parsed under %s", src_dir)
        return 0

    fields = [
        "note_id", "year", "date", "interviewee", "company",
        "title", "duration_sec", "transcript_len", "tags",
        "audio_url", "source_path",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    log.info("wrote %d rows → %s", len(rows), out_csv)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize 1-data/<year>/*.md → 2-processing/<year>/notes.csv")
    parser.add_argument("--year", type=int, required=True)
    args = parser.parse_args()
    return run(args.year)


if __name__ == "__main__":
    sys.exit(0 if main() >= 0 else 1)