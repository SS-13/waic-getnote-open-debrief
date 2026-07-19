"""Render interview-report cards (HTML → PNG) from 2-processing/<year>/notes.md.

Reads the 0717 dialog notes, splits into per-interview cards, renders each into
the HTML template at templates/report_card.html, screenshots at 1080x1440
via Playwright (headless Chromium), and writes to 3-outputs/<year>/reports/<date>/.

Usage:
    python scripts/render_reports.py --year 2026 --date 2026-07-17
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[1]


# Lightweight settings stand-in: we only need repo_root for this script.
class _Settings:
    repo_root = REPO_ROOT


settings = _Settings()


# ---------- 笔记解析 ----------

_SECTION_RE = re.compile(r"^##\s+访谈([一二三四五六七八九十百零\d]+)：(.+?)\s*$")
_ASKER_RE = re.compile(r"^###\s*(罗振宇提问|快刀青衣提问|罗振宇/快刀青衣提问重点|快刀青衣/罗振宇提问重点)\s*$")
_ANSWER_HEADER_RE = re.compile(r"^###\s*回答摘要\s*$")
_HR_RE = re.compile(r"^---\s*$")

# 中文数字 → 阿拉伯数字（支持 一/二/...十、十一/十二/...十九、二十/二十一/...）
_CN_DIGIT = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "零": 0}


def _cn_to_int(s: str) -> int:
    if s.isdigit():
        return int(s)
    if s == "十":
        return 10
    if "十" in s:
        parts = s.split("十")
        tens = _CN_DIGIT.get(parts[0], 1) if parts[0] else 1
        ones = _CN_DIGIT.get(parts[1], 0) if parts[1] else 0
        return tens * 10 + ones
    return _CN_DIGIT.get(s, 0)


def _safe_filename(name: str) -> str:
    """Convert '11-奇岱松科技黄真-空间知识赋能多机器人协作-.png' style."""
    # 清理标点
    cleaned = re.sub(r"[^\w一-鿿-]+", "-", name).strip("-")
    return cleaned


def parse_interviews(md_path: Path) -> list[dict]:
    """Parse one dialog-notes .md into per-interview dicts.

    Each dict: {index, title, asker, questions: [str,...], answer: str}
    """
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    interviews: list[dict] = []
    current: dict | None = None
    state = "idle"  # idle | questions | answer

    for line in lines:
        m = _SECTION_RE.match(line)
        if m:
            if current:
                interviews.append(current)
            current = {
                "index": _cn_to_int(m.group(1)),
                "title": m.group(2).strip(),
                "asker": "",
                "questions": [],
                "answer": "",
            }
            state = "idle"
            continue
        if current is None:
            continue

        if state == "idle":
            am = _ASKER_RE.match(line)
            if am:
                tag = am.group(1)
                if "快刀青衣/罗振宇" in tag:
                    current["asker"] = "快刀青衣 + 罗振宇"
                elif "快刀青衣" in tag:
                    current["asker"] = "快刀青衣"
                else:
                    current["asker"] = "罗振宇"
                state = "questions"
                continue
        elif state == "questions":
            qm = re.match(r'^\s*-\s*[""]?(.+?)[""]?\s*$', line)
            if qm:
                current["questions"].append(qm.group(1))
                continue
            if _ANSWER_HEADER_RE.match(line):
                state = "answer"
                continue
            # 段间分隔
            if _HR_RE.match(line) or line.strip() == "":
                continue
        elif state == "answer":
            if _HR_RE.match(line) or _SECTION_RE.match(line):
                # 结束当前访谈
                interviews.append(current)
                current = None
                state = "idle"
                if _SECTION_RE.match(line):
                    # 让外层下一轮再处理这个 section
                    nm = _SECTION_RE.match(line)
                    current = {
                        "index": _cn_to_int(nm.group(1)),
                        "title": nm.group(2).strip(),
                        "asker": "",
                        "questions": [],
                        "answer": "",
                    }
                    state = "idle"
                continue
            if line.strip():
                current["answer"] += ("\n" if current["answer"] else "") + line.strip()

    if current:
        interviews.append(current)

    # 清理 answer 收尾空白
    for it in interviews:
        it["answer"] = it["answer"].strip()
    return interviews


# ---------- 渲染 ----------

TEMPLATE_PATH = settings.repo_root / "templates"
TEMPLATE_NAME = "report_card.html"


def render_html(jinja_env, iv: dict) -> str:
    """Render one interview into the HTML template via Jinja2."""
    tmpl = jinja_env.get_template(TEMPLATE_NAME)
    return tmpl.render(
        index=f"{iv['index']:02d}",
        title=iv["title"],
        asker=iv["asker"],
        questions=iv["questions"],
        answer=iv["answer"].replace("\n", "<br/>"),
    )


def render_one(page, html: str, out_png: Path) -> None:
    """Load HTML into browser, screenshot to PNG."""
    page.set_content(html, wait_until="networkidle")
    # 等中文字体 ready
    page.evaluate("document.fonts.ready")
    locator = page.locator(".page")
    locator.screenshot(path=str(out_png), omit_background=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--date", required=True, help="e.g. 2026-07-17")
    args = parser.parse_args()

    proc_dir = settings.repo_root / "2-processing" / str(args.year)
    out_dir = settings.repo_root / "3-outputs" / str(args.year) / "reports" / args.date.replace("-", "")[4:]
    out_dir.mkdir(parents=True, exist_ok=True)

    # 按 --date 筛对话录（中文日期 "7月18日"）
    candidates = sorted(proc_dir.glob("*对话录：提问与回答摘要*.md"))
    iso = args.date  # e.g. "2026-07-18"
    m, d = iso[5:7].lstrip("0"), iso[8:10].lstrip("0")
    needle = f"{m}月{d}日"
    filtered = [p for p in candidates if needle in p.name]
    if filtered:
        candidates = filtered

    if not candidates:
        print(f"ERROR: no dialog notes found under {proc_dir}", file=sys.stderr)
        return 1
    notes_path = candidates[0]
    print(f"reading: {notes_path}")

    interviews = parse_interviews(notes_path)
    print(f"parsed {len(interviews)} interviews")

    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_PATH)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # 启动 playwright
    from playwright.sync_api import sync_playwright

    rendered = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        page = context.new_page()

        for iv in interviews:
            html = render_html(jinja_env, iv)
            # 文件名：NN-标题短横杠化-.png
            safe_title = _safe_filename(iv["title"])
            out_png = out_dir / f"{iv['index']:02d}-{safe_title}-.png"
            render_one(page, html, out_png)
            print(f"  ✓ {out_png.name}")
            rendered += 1

        browser.close()

    print(f"done: {rendered} PNG(s) → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
