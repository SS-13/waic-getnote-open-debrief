"""Daily incremental sync of getnote KB -> 1-raw/.

Pulls only NEW notes (by note_id) that don't yet exist locally. Classifies
into the same year/content-type tree as the initial setup. Regenerates
1-raw/INDEX.md at the end. Safe to run any number of times per day —
it's a no-op if KB hasn't grown.

Usage:
    python scripts/daily_sync.py                 # one-shot sync
    python scripts/daily_sync.py --dry-run       # report diff, no fetch
    python scripts/daily_sync.py --no-reindex    # skip INDEX rebuild

Cron (every day 09:07 local):
    7 9 * * * cd /path/to/repo && python scripts/daily_sync.py >> .sync.log 2>&1
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW  = REPO / "1-raw"
TOPIC = "JawjeBlY"  # 2026 WAIC 知识库
YEARS = ["2018","2019","2020","2021","2022","2023","2024","2025"]

def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def run_cli(*args: str) -> str:
    r = subprocess.run(["getnote", *args, "-o", "json"], capture_output=True, text=True, check=True)
    return r.stdout

def kb_index() -> list[dict]:
    data = json.loads(run_cli("kb", TOPIC, "--all", "--no-content"))
    return data["data"]["notes"]

def local_ids() -> set[str]:
    ids: set[str] = set()
    for f in RAW.rglob("*.md"):
        if f.name in {"README.md", "INDEX.md"}: continue
        m = re.search(r'^note_id:\s*(\d+)', f.read_text(encoding="utf-8", errors="ignore")[:600], re.M)
        if m: ids.add(m.group(1))
    return ids

def safe_name(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[\\/:*?"<>|]+', "-", name)
    name = re.sub(r"\s+", "_", name).strip("_-")
    return name[:max_len].rstrip("_-") if len(name) > max_len else name

def classify(n: dict) -> str:
    """Return relative path under 1-raw/ (excluding the year file name)."""
    def tagstr(n) -> str:
        return " ".join((t.get("name") if isinstance(t, dict) else str(t)) for t in (n.get("tags") or []))
    tg = tagstr(n); t = (n.get("title") or ""); nt = n.get("note_type"); d = (n.get("created_at") or "")[:10]
    yr = next((y for y in YEARS if y in tg), None)
    if yr is None:
        yr = next((y for y in YEARS if y in t), None)
    if yr:
        return f"往年届次/WAIC-{yr}"
    if ("治理" in t or "治理" in tg or "全球南方" in tg) and d and d >= "2026-07-19":
        return "专题研究"
    if nt in ("local_audio", "recorder_audio") or "录音" in tg or "流水席" in t or "云逛展" in t or "云游展" in t:
        return "WAIC-2026当届/现场录音实录"
    if re.search(r"[·｜|]", t) and d >= "2026-07-18":
        return "WAIC-2026当届/论坛演讲实录"
    return "WAIC-2026当届/资讯与链接"

def write_note(n: dict) -> Path:
    nid = str(n["note_id"])
    raw = run_cli("note", nid)
    full = json.loads(raw)["data"]["note"]
    title = full.get("title") or n.get("title") or "(no title)"
    created = full.get("created_at") or n.get("created_at") or ""
    content = (full.get("content") or "").strip()
    d = created.split(" ")[0] if created else "unknown-date"
    folder = RAW / classify(n)
    folder.mkdir(parents=True, exist_ok=True)
    # de-dup filename: date + safe title + note_id suffix if exists
    base = f"{d}__{safe_name(title)}.md"
    path = folder / base
    if path.exists():
        path = folder / f"{d}__{safe_name(title, 60)}__{nid[-6:]}.md"
    fm = (
        "---\n"
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        "author: Joe\n"
        f"date: {d}\n"
        "source: getnote\n"
        f"note_id: {nid}\n"
        f"captured_at: {created}\n"
        f"original_url: https://www.biji.com/note/{nid}\n"
        "---\n\n"
    )
    path.write_text(fm + content + "\n", encoding="utf-8")
    return path

def rebuild_index() -> None:
    from collections import defaultdict
    files = [f for f in RAW.rglob("*.md") if f.name not in {"README.md", "INDEX.md"}]
    # stats
    by_folder: dict[str, int] = defaultdict(int)
    for f in files: by_folder[str(f.relative_to(RAW).parent)] += 1
    L: list[str] = []
    L.append("# 📚 1-raw/ 内部索引\n")
    L.append(f"> 来源 KB：**2026 WAIC 知识库**（topic `{TOPIC}`）")
    L.append(f"> 索引更新时间：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    L.append("## 目录与篇数\n")
    L.append("| 目录 | 篇数 | 说明 |")
    L.append("|---|---:|---|")
    DESC = {
        "WAIC-2026当届/现场录音实录": "流水席 / 论坛现场录音（getnote AI 摘要；完整逐字稿见 2-data）",
        "WAIC-2026当届/论坛演讲实录": "2026 论坛嘉宾演讲、致辞、圆桌",
        "WAIC-2026当届/资讯与链接": "2026 官方资讯 / 报道 / 链接",
        "专题研究": "跨年 AI 治理 / 研究类深度文章",
        "往年届次/WAIC-2025": "2025 WAIC 资料存档",
        "往年届次/WAIC-2024": "2024 WAIC 资料存档",
        "往年届次/WAIC-2023": "2023 WAIC 资料存档",
        "往年届次/WAIC-2022": "2022 WAIC 资料存档",
        "往年届次/WAIC-2021": "2021 WAIC 资料存档",
        "往年届次/WAIC-2020": "2020 WAIC 资料存档",
        "往年届次/WAIC-2019": "2019 WAIC 资料存档",
        "往年届次/WAIC-2018": "2018 WAIC 资料存档",
    }
    for k in sorted(by_folder):
        L.append(f"| `{k}/` | {by_folder[k]} | {DESC.get(k,'')} |")
    L.append(f"| **合计** | **{sum(by_folder.values())}** | |")
    L.append("\n## 维护机制\n")
    L.append("- **去重唯一键**：每篇 frontmatter 的 `note_id`")
    L.append("- **每日增量**：`python scripts/daily_sync.py`（或挂 cron，详见 `scripts/daily_sync.py` 顶部说明）")
    L.append("- **外部索引**：`3-processing/index/waic-kb-pull-index.md` 833 条全量清单（按目录分组）")
    (RAW / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="only show diff, no fetch")
    ap.add_argument("--no-reindex", action="store_true", help="skip INDEX.md rebuild")
    args = ap.parse_args()

    log("fetching KB index …")
    notes = kb_index()
    have = local_ids()
    todo = [n for n in notes if str(n["note_id"]) not in have]
    log(f"KB total: {len(notes)} | local: {len(have)} | new: {len(todo)}")

    by_date: Counter = Counter(n.get("created_at", "")[:10] for n in todo)
    for d in sorted(by_date): log(f"  +{by_date[d]:>4} {d}")

    if args.dry_run:
        log("dry-run, exiting."); return 0
    if not todo:
        log("nothing to sync."); 
    else:
        ok = fail = 0
        for i, n in enumerate(todo, 1):
            try:
                p = write_note(n)
                ok += 1
                log(f"[{i}/{len(todo)}] ✓ {p.relative_to(REPO)}")
            except subprocess.CalledProcessError as e:
                fail += 1
                log(f"[{i}/{len(todo)}] ✗ {n['note_id']}: {e.stderr.strip()[:120]}")
        log(f"fetched: {ok} | failed: {fail}")

    if not args.no_reindex:
        log("rebuilding 1-raw/INDEX.md …")
        rebuild_index()
        log("done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
