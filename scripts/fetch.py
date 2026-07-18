"""Fetch WAIC notes from getnote API (slow + resumable).

Single-file design:
- Token-bucket rate limiter (RPS + daily quota)
- Persistent checkpoint for resume
- Dry-run mode when no API key is set
- Saves raw notes to data/<year>/<date>__<interviewee>.md

Usage:
    python scripts/fetch.py --year 2025
    python scripts/fetch.py --year 2025 --since 2025-07-01 --until 2025-07-31
    python scripts/fetch.py --year 2025 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from scripts.config import settings

# ---------- logging ----------

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fetch")


# ---------- rate limiter ----------

@dataclass
class _Bucket:
    tokens: float
    last_refill: float
    daily_used: int = 0
    daily_date: date = field(default_factory=date.today)


class RateLimiter:
    def __init__(self, rps: float, burst: int, daily_quota: int) -> None:
        self._rps = rps
        self._burst = burst
        self._quota = daily_quota
        self._lock = threading.Lock()
        self._b = _Bucket(tokens=float(burst), last_refill=time.monotonic())

    def _refill(self) -> None:
        elapsed = time.monotonic() - self._b.last_refill
        self._b.tokens = min(float(self._burst), self._b.tokens + elapsed * self._rps)
        self._b.last_refill = time.monotonic()

    def acquire(self, timeout: float | None = None) -> bool:
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._lock:
            self._maybe_reset_daily()
            if self._quota and self._b.daily_used >= self._quota:
                log.error("daily quota exhausted (%d/%d)", self._b.daily_used, self._quota)
                return False
            while True:
                self._refill()
                if self._b.tokens >= 1.0:
                    self._b.tokens -= 1.0
                    self._b.daily_used += 1
                    return True
                if deadline is not None and time.monotonic() >= deadline:
                    return False
                sleep_for = max(0.0, (1.0 - self._b.tokens) / self._rps)
                self._lock.release()
                try:
                    time.sleep(min(sleep_for, 1.0))
                finally:
                    self._lock.acquire()
                self._maybe_reset_daily()
                if self._quota and self._b.daily_used >= self._quota:
                    return False

    def _maybe_reset_daily(self) -> None:
        if date.today() != self._b.daily_date:
            log.info("new day, resetting daily counter")
            self._b.daily_date = date.today()
            self._b.daily_used = 0


# ---------- checkpoint ----------

class Checkpoint:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        if not self._path.exists():
            return {"fetched_ids": [], "cursor": None}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {"fetched_ids": [], "cursor": None}

    def is_done(self, note_id: str) -> bool:
        return note_id in self._data["fetched_ids"]

    def mark_done(self, note_id: str) -> None:
        with self._lock:
            if note_id not in self._data["fetched_ids"]:
                self._data["fetched_ids"].append(note_id)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )


# ---------- channels ----------

@retry(
    retry=retry_if_exception_type((httpx.HTTPError,)),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _http_list_page(client: httpx.Client, since: str, until: str, cursor: str | None) -> dict:
    params: dict[str, str] = {"since": since, "until": until}
    if cursor:
        params["cursor"] = cursor
    resp = client.get("/v1/notes", params=params)
    resp.raise_for_status()
    return resp.json()


def http_channel(year: int, since: str, until: str) -> Iterator[dict]:
    client = httpx.Client(
        base_url=settings.getnote.api_base,
        timeout=httpx.Timeout(20.0, read=60.0),
        headers={
            "Authorization": f"Bearer {settings.getnote.api_key}",
            "X-User-Token": settings.getnote.user_token,
        },
    )
    cursor = None
    try:
        while True:
            page = _http_list_page(client, since, until, cursor)
            for raw in page.get("notes", []):
                yield _normalize_record(raw, year=year)
            cursor = page.get("next_cursor")
            if not cursor:
                return
    finally:
        client.close()


def dry_run_channel(year: int, since: str, until: str) -> Iterator[dict]:
    """Fake channel for pipeline validation without API access."""
    start = datetime.fromisoformat(since)
    end = datetime.fromisoformat(until)
    from datetime import timedelta
    cur = start
    i = 0
    while cur <= end:
        for j in range(3):  # 3 fake notes per day
            i += 1
            yield {
                "note_id": f"dryrun-{cur.strftime('%Y%m%d')}-{j:02d}",
                "year": year,
                "date": cur.strftime("%Y-%m-%d"),
                "interviewee": f"Interviewee #{i}",
                "company": f"Company #{i}",
                "title": f"[dryrun] WAIC interview {i}",
                "duration_sec": 600 + i * 10,
                "transcript": f"placeholder transcript for note {i}",
                "audio_url": None,
                "tags": ["dry-run", "waic"],
            }
        cur += timedelta(days=1)


def _normalize_record(raw: dict, year: int) -> dict:
    captured = raw.get("captured_at", "")
    return {
        "note_id": str(raw["id"]),
        "year": year,
        "date": captured[:10] if captured else "",
        "interviewee": raw.get("interviewee", ""),
        "company": raw.get("interviewee_company", ""),
        "title": raw.get("title", ""),
        "duration_sec": raw.get("duration_sec", 0),
        "transcript": raw.get("transcript", ""),
        "audio_url": raw.get("audio_url"),
        "tags": raw.get("tags", []),
    }


# ---------- persistence ----------

def save_note(year: int, note: dict) -> Path:
    date_part = note.get("date") or "unknown-date"
    name_part = (note.get("company") or note.get("interviewee") or note["note_id"]).strip()
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name_part)
    target = settings.repo_root / "data" / str(year) / f"{date_part}__{safe}.md"
    target.parent.mkdir(parents=True, exist_ok=True)

    body = f"""# {note.get('title', '(no title)')}

- **date**: {note.get('date', '')}
- **interviewee**: {note.get('interviewee', '')}
- **company**: {note.get('company', '')}
- **duration_sec**: {note.get('duration_sec', 0)}
- **tags**: {', '.join(note.get('tags', []))}
- **note_id**: {note.get('note_id', '')}
- **audio_url**: {note.get('audio_url') or '(none)'}

---

## Transcript

{note.get('transcript', '(empty)')}
"""
    target.write_text(body, encoding="utf-8")
    return target


# ---------- main ----------

def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch WAIC notes into data/<year>/")
    parser.add_argument("--year", type=int, required=True, help="e.g. 2025")
    parser.add_argument("--since", required=True, help="ISO date, e.g. 2025-07-01")
    parser.add_argument("--until", required=True, help="ISO date, e.g. 2025-07-31")
    parser.add_argument("--dry-run", action="store_true", help="skip network, use fake data")
    args = parser.parse_args()

    limiter = RateLimiter(
        rps=settings.rate_limit.rps,
        burst=settings.rate_limit.burst,
        daily_quota=settings.rate_limit.daily_quota,
    )
    cp = Checkpoint(settings.state_path)

    use_dry = args.dry_run or not settings.getnote.api_key
    if use_dry:
        log.warning("DRY-RUN mode (no real API calls)")
        source = dry_run_channel(args.year, args.since, args.until)
    else:
        source = http_channel(args.year, args.since, args.until)

    saved = skipped = 0
    for note in source:
        if cp.is_done(note["note_id"]):
            skipped += 1
            continue
        if not limiter.acquire():
            log.warning("rate limiter blocked at saved=%d skipped=%d", saved, skipped)
            break
        try:
            save_note(args.year, note)
            cp.mark_done(note["note_id"])
            saved += 1
            if saved % 25 == 0:
                log.info("progress: saved=%d skipped=%d", saved, skipped)
        except Exception as exc:
            log.exception("save failed for %s: %s", note.get("note_id"), exc)

    cp.save()
    log.info("done: year=%d saved=%d skipped=%d", args.year, saved, skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())