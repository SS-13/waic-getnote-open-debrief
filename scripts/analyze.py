"""Example analyzers operating on 2-processing/<year>/notes.csv.

Currently supports:
- --kind companies   → 2-processing/<year>/companies.csv (mention frequency)
- --kind yearly      → 3-outputs/<year>/reports/yearly_summary.json (high-level stats)

Usage:
    python scripts/analyze.py --year 2025 --kind companies
    python scripts/analyze.py --year 2025 --kind yearly
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path

from scripts.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("analyze")


def _read_notes_csv(year: int) -> list[dict]:
    csv_path = settings.repo_root / "2-processing" / str(year) / "notes.csv"
    if not csv_path.exists():
        log.error("missing %s — run scripts/normalize.py first", csv_path)
        return []
    with csv_path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def kind_companies(year: int) -> int:
    rows = _read_notes_csv(year)
    company_mentions: Counter[str] = Counter()
    company_note_count: Counter[str] = Counter()
    for r in rows:
        c = r.get("company", "").strip()
        if not c:
            continue
        company_note_count[c] += 1

    # Mention = note_count for now; extend by scanning transcripts for "<company>" hits
    for r in rows:
        transcript_path = settings.repo_root / r.get("source_path", "")
        if transcript_path.exists():
            text = transcript_path.read_text(encoding="utf-8")
            for c in company_note_count:
                company_mentions[c] += text.count(c)

    out_dir = settings.repo_root / "2-processing" / str(year)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "companies.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["company", "mentions", "note_count"])
        for c, cnt in company_note_count.most_common():
            w.writerow([c, company_mentions.get(c, cnt), cnt])
    log.info("wrote %s (rows=%d)", out_csv, len(company_note_count))
    return len(company_note_count)


def kind_yearly(year: int) -> int:
    rows = _read_notes_csv(year)
    out_dir = settings.repo_root / "3-outputs" / str(year) / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    by_date: Counter[str] = Counter()
    by_company: Counter[str] = Counter()
    total_minutes = 0
    for r in rows:
        by_date[r.get("date", "")] += 1
        c = r.get("company", "").strip()
        if c:
            by_company[c] += 1
        try:
            total_minutes += int(r.get("duration_sec", 0) or 0) / 60
        except ValueError:
            pass

    summary = {
        "year": year,
        "total_notes": total,
        "total_company_appearances": sum(by_company.values()),
        "unique_companies": len(by_company),
        "approx_total_minutes": round(total_minutes, 1),
        "by_date_top10": by_date.most_common(10),
        "top_companies_top10": by_company.most_common(10),
    }
    out = out_dir / "yearly_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("wrote %s", out)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an analyzer on 2-processing/<year>/notes.csv")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument(
        "--kind",
        required=True,
        choices=["companies", "yearly"],
        help="which analysis to run",
    )
    args = parser.parse_args()

    if args.kind == "companies":
        n = kind_companies(args.year)
    elif args.kind == "yearly":
        n = kind_yearly(args.year)
    else:
        n = 0

    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())