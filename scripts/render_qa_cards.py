"""Render interview-report cards from the new QA format.

Reads 2-processing/<date>/<file>.md with format:
    ## 访谈N：公司名（描述）
    ### 提问清单（N 个）
    01. **主题1**
    02. **主题2**
    ...
    ### 回答摘要
    - **主题1**：正文
    - **主题2**：正文
    ...

Renders each interview into templates/report_card.html via Playwright.

Usage:
    python scripts/render_qa_cards.py --day 2026-07-17
    python scripts/render_qa_cards.py --day 2026-07-18
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates"
TEMPLATE_NAME = "report_card.html"

# 17 号上午（罗振宇开场）→ 罗振宇；17 号下午 → 交替
# 18 号上午 → 罗振宇+快刀青衣 混合（按访谈顺序交替）
# 简化：按访谈序号奇偶分配
# 但更好：根据源稿判断
# 这里直接用公司→提问人映射（按老对话录）

ASKER_BY_TITLE_HINT = {
    "云深处": "罗振宇",
    "千寻智能": "快刀青衣",
    "交泰智能": "罗振宇",
    "绳机妙算": "快刀青衣",
    "陶氏智能": "罗振宇",
    "上海永轴": "快刀青衣",
    "灵犀科技": "快刀青衣",
    "Workbody": "快刀青衣",
    "佳智科技": "罗振宇",  # 兼容老 alias
    "迦智科技": "罗振宇",  # 17 号 09 + 18 号 15 实际是"迦智科技"
    "科大讯飞": "快刀青衣",
    "奇岱松": "罗振宇",
    "松应": "快刀青衣",
    "iEarth": "快刀青衣",
    "凌迪科技": "快刀青衣",
    "东浩兰生": "罗振宇",
    "南方电网": "罗振宇",
    "数字生命卡兹克": "快刀青衣",
    "核心数科": "快刀青衣",
    "开普勒": "罗振宇",
    "灵样AI": "快刀青衣",
    "灵动章鱼": "快刀青衣",
    "原生先达": "快刀青衣",
    "心意智能": "罗振宇",
    "库帕斯": "快刀青衣",
    "知情智能": "快刀青衣",
    "念极智能": "罗振宇",
    "维他动力": "快刀青衣",
    "一家和李小阳": "罗振宇",
    "上海音乐学院": "快刀青衣",
    "陈小天": "罗振宇",
    "灵初智能": "快刀青衣",
    "国华智能": "罗振宇",
    "玄机若兰": "快刀青衣",
    "迦智科技": "快刀青衣",
    "气象局": "罗振宇",
    "盟友智能": "快刀青衣",
    "清华大学机器人足球": "罗振宇",
    "福鑫科技": "快刀青衣",
    "WAIC特刊主编": "罗振宇",
}


def detect_asker(title: str) -> str:
    """根据公司名匹配提问人"""
    for hint, asker in ASKER_BY_TITLE_HINT.items():
        if hint in title:
            return asker
    return "罗振宇 + 快刀青衣"


def parse_qa_file(md_path: Path) -> list[dict]:
    """Parse new-format QA markdown → list of {title, questions[], answer}"""
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    interviews = []
    current = None
    in_questions = False
    in_answer = False
    pending_q = None  # 收集 01. **主题** 的主题名

    SECTION_RE = re.compile(r"^##\s+访谈(.+?)：(.+?)\s*$")
    Q_HEAD_RE = re.compile(r"^###\s*提问清单.*$")
    A_HEAD_RE = re.compile(r"^###\s*回答摘要\s*$")
    Q_LINE_RE = re.compile(r"^(\d+)\.\s+\*\*(.+?)\*\*\s*$")
    A_LINE_RE = re.compile(r"^-\s+\*\*(.+?)\*\*[：:]\s*(.+)$")

    for ln in lines:
        m = SECTION_RE.match(ln)
        if m:
            if current:
                interviews.append(current)
            current = {
                "title": m.group(2).strip(),
                "questions": [],
                "answer_map": {},
                "asker": detect_asker(m.group(2).strip()),
            }
            in_questions = in_answer = False
            continue

        if current is None:
            continue

        if Q_HEAD_RE.match(ln):
            in_questions = True
            in_answer = False
            continue
        if A_HEAD_RE.match(ln):
            in_questions = False
            in_answer = True
            continue
        # 章节标题切换会清状态
        if ln.startswith("## ") and not SECTION_RE.match(ln):
            in_questions = in_answer = False

        if in_questions:
            qm = Q_LINE_RE.match(ln.strip())
            if qm:
                current["questions"].append(qm.group(2).strip())

        if in_answer:
            am = A_LINE_RE.match(ln.strip())
            if am:
                theme = am.group(1).strip()
                body = am.group(2).strip()
                current["answer_map"][theme] = body

    if current:
        interviews.append(current)

    # 过滤掉没有 questions 的
    return [iv for iv in interviews if iv["questions"]]


def render_one(jinja_env, iv: dict, index: int) -> str:
    tmpl = jinja_env.get_template(TEMPLATE_NAME)
    questions = []
    for q in iv["questions"]:
        # 答案直接来自 answer_map；如果缺失则用问号占位
        ans = iv["answer_map"].get(q, "（回答摘要见对话录）")
        questions.append({"q": q, "a": ans})
    return tmpl.render(
        index=f"{index:02d}",
        title=iv["title"],
        asker=iv["asker"],
        questions=questions,
        answer="\n".join(f"{q['q']}：{q['a']}" for q in questions),
    )


def safe_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r"[\\/:*?\"<>|]+", "-", name)
    name = re.sub(r"\s+", "_", name).strip("_-")
    if len(name) > max_len:
        name = name[:max_len].rstrip("_-")
    return name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", required=True, help="e.g. 2026-07-17")
    args = parser.parse_args()

    # 找当天 QA 文件
    proc_dir = REPO_ROOT / "2-processing" / "2026"
    iso = args.day
    m, d = iso[5:7].lstrip("0"), iso[8:10].lstrip("0")
    needle = f"{m}月{d}日"
    candidates = sorted(proc_dir.glob(f"*/*{needle}*对话录：提问与回答摘要*.md"))
    candidates += sorted(proc_dir.glob(f"*/*{needle}*提问与回答摘要*.md"))
    candidates = list({c.resolve(): c for c in candidates}.values())
    if not candidates:
        print(f"ERROR: no QA file found under {proc_dir}/*/{needle}*", file=sys.stderr)
        return 1
    qa_path = candidates[0]
    print(f"reading: {qa_path}")

    interviews = parse_qa_file(qa_path)
    print(f"parsed {len(interviews)} interviews")

    # 输出目录
    day_short = iso.replace("-", "")[4:]
    out_dir = REPO_ROOT / "3-outputs" / "2026" / "reports" / day_short
    # 备份旧文件到 _old 子目录（owner 之前 0718 的图是另一批）
    if out_dir.exists():
        backup = out_dir.parent / f"{day_short}_old"
        if backup.exists():
            shutil.rmtree(backup)
        shutil.move(str(out_dir), str(backup))
        print(f"backup: old → {backup.relative_to(REPO_ROOT)}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Jinja2 + Playwright
    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    from playwright.sync_api import sync_playwright

    rendered = 0
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1080, "height": 1440},
            device_scale_factor=2,
        )
        page = context.new_page()

        for i, iv in enumerate(interviews, 1):
            html = render_one(jinja_env, iv, i)
            safe_title = safe_filename(iv["title"])
            out_png = out_dir / f"{i:02d}-{safe_title}-.png"
            page.set_content(html, wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            # 改用 full_page 截图，让 page 自适应高度
            page.screenshot(path=str(out_png), full_page=True, omit_background=False)
            print(f"  ✓ {out_png.name}")
            rendered += 1

        browser.close()

    print(f"\ndone: {rendered} PNG(s) → {out_dir.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
