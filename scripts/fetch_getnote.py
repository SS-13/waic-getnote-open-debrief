"""Fetch WAIC notes from getnote via @getnote/cli into 1-data/<year>/.

Default behavior (no flags): pull the 02 直播总结 note only.
Usage:
    # Pull a single note
    python scripts/fetch_getnote.py --note-id 1915855211323387872

    # Pull all notes in a topic (728 notes for JawjeBlY — heavy)
    python scripts/fetch_getnote.py --topic-id JawjeBlY --all

    # Pull only topic notes newer than a date
    python scripts/fetch_getnote.py --topic-id JawjeBlY --since 2026-07-17
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> str:
    """Run @getnote/cli and capture stdout."""
    cmd = ["npx", "-y", "@getnote/cli", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return proc.stdout


def fetch_note_content(note_id: int | str) -> str:
    """Fetch the markdown content of a single note."""
    return _run_cli("note", str(note_id), "--field", "content")


def fetch_note_meta(note_id: int | str) -> dict:
    """Fetch note metadata via JSON listing trick (cheaper than /note)."""
    # We use --field for content + a separate full-JSON fetch for metadata
    raw = _run_cli("note", str(note_id), "-o", "json")
    return json.loads(raw)["data"]


def fetch_topic_index(topic_id: str, no_content: bool = True, all_pages: bool = True) -> list[dict]:
    """Fetch the index of notes in a topic."""
    args = ["kb", topic_id, "-o", "json"]
    if no_content:
        args.append("--no-content")
    if all_pages:
        args.append("--all")
    raw = _run_cli(*args)
    return json.loads(raw)["data"]["notes"]


def safe_filename(name: str, max_len: int = 80) -> str:
    """Make a filesystem-safe filename from a Chinese title."""
    # 保留中文 + ASCII 字母数字 + 横线
    name = re.sub(r"[\\/:*?\"<>|]+", "-", name)
    name = re.sub(r"\s+", "_", name).strip("_-")
    if len(name) > max_len:
        name = name[:max_len].rstrip("_-")
    return name


def write_note(out_dir: Path, note: dict, content: str) -> Path:
    """Write one note as markdown with frontmatter into 1-data/<year>/."""
    out_dir.mkdir(parents=True, exist_ok=True)
    title = note["title"]
    note_id = note["note_id"]
    created_at = note.get("created_at", "")
    date_iso = created_at.split(" ")[0] if created_at else "unknown-date"
    safe = safe_filename(title)
    fname = f"{date_iso}__{safe}.md"
    path = out_dir / fname

    frontmatter = (
        "---\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        f"author: Joe\n"
        f"date: {date_iso}\n"
        f"source: getnote\n"
        f"note_id: {note_id}\n"
        f"captured_at: {created_at}\n"
        f"original_url: https://www.biji.com/note/{note_id}\n"
        "---\n\n"
    )
    path.write_text(frontmatter + content.strip() + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--note-id", help="Fetch a single note by its note_id")
    parser.add_argument("--topic-id", help="Fetch notes in a topic")
    parser.add_argument("--all", action="store_true", help="Fetch all pages of a topic")
    parser.add_argument(
        "--since",
        help="Only fetch notes with created_at >= this date (YYYY-MM-DD)",
    )
    args = parser.parse_args()

    out_dir = REPO_ROOT / "1-data" / str(args.year)
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    if args.note_id:
        # Single-note mode
        print(f"fetching note_id={args.note_id} ...")
        content = fetch_note_content(args.note_id)
        meta = fetch_note_meta(args.note_id)
        note = {
            "note_id": args.note_id,
            "title": meta.get("title", "(no title)"),
            "created_at": meta.get("created_at", ""),
        }
        path = write_note(out_dir, note, content)
        written.append(path)
        print(f"  ✓ {path.relative_to(REPO_ROOT)}  ({len(content)} chars)")
    elif args.topic_id:
        # Topic-batch mode
        print(f"fetching topic={args.topic_id} index ...")
        notes = fetch_topic_index(args.topic_id, no_content=True, all_pages=args.all)
        print(f"  indexed {len(notes)} notes")

        if args.since:
            notes = [n for n in notes if n.get("created_at", "") >= args.since]
            print(f"  filtered to {len(notes)} notes since {args.since}")

        for i, n in enumerate(notes, 1):
            try:
                content = fetch_note_content(n["note_id"])
                path = write_note(out_dir, n, content)
                written.append(path)
                print(f"  [{i}/{len(notes)}] ✓ {path.name}  ({len(content)} chars)")
            except subprocess.CalledProcessError as e:
                print(f"  [{i}/{len(notes)}] ✗ note_id={n['note_id']}: {e}", file=sys.stderr)
    else:
        parser.error("Provide --note-id or --topic-id")

    print(f"\ndone: {len(written)} file(s) → {out_dir.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
