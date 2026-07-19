"""Render 18 号两个长图：dashboard.html + question_list.html.

数据源：
- dashboard: 2-processing/2026/0718/07月18日WAIC流水席对话录：提问与回答摘要.md
  → 每家公司的 4 方向聚类（按主题块关键词）
- question_list: 2-processing/2026/0718/07月18日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md
  → 保留 🆕 / ♻️ 标记

输出：3-outputs/2026/figures/0718-dashboard.png + 0718-question-list.png
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = REPO_ROOT / "templates"


# ====== dashboard 4 方向关键词聚类 ======
DIR_KEYWORDS = {
    1: ("技术路线", ["技术", "研发", "攻坚", "路线", "参数", "工艺", "技术路线", "难点", "核心难点", "数据手套", "材料", "自研"]),
    2: ("落地场景", ["场景", "落地", "案例", "应用", "客户", "效果", "测试", "分拣", "调音", "康复", "种植", "灾害预警", "复盘"]),
    3: ("时间表", ["未来", "时间", "爆发", "预测", "趋势", "发展", "24个月", "前景", "3年", "5年", "2030", "2050", "上市", "上线", "时间预测"]),
    4: ("成本可及性", ["价格", "成本", "定价", "免费", "降价", "便宜", "营收", "价", "市场", "盈利", "商业化", "盈利模式", "市场前景"]),
}

DIR_QUOTES = {
    1: [
        "在什么阶段？用什么量化指标判定，不是概念。",
        "“技术路线是什么 / 相比传统有什么优势”",
        "“能效提升多少 / 寿命多长 / 负载多少”",
    ],
    2: [
        "不要 PPT，要客户名 + 准确率 + 节拍数据。",
        "“在哪些客户那里落地了 / 效果怎么样”",
        "“能举一个具体的应用案例吗”",
    ],
    3: [
        "什么技术什么时候能到什么程度？给一个时间锚。",
        "“3-5 年内能做到什么程度 / 什么时候能进家庭”",
        "“未来 1-2 年哪个领域最可能爆发”",
    ],
    4: [
        "技术能不能普惠，让更多人、中小企业、文科生都用上。",
        "“价格能做到多低 / 砍掉了哪些功能”",
        "“文科生能不能进入 / 未来怎么降本”",
    ],
}
DIR_ANSWERS = {
    1: "技术制度：行星滚柱丝杠、3-5W 能耗、40g 全球最轻、3-5W 能耗",
    2: "场景纵深：黄金冶炼厂磨机、宁德时代 99.5%、京东双井咖啡、20% 三甲医院",
    3: "产业节拍：机器狗 1-2 年、家用机器人 3-5 年、AI 科研 1-3 年",
    4: "普惠曲线：3500 元灵巧手、1/4 价减速器、机器人 10 万 → 3 万",
}
DIR_TAKEAWAYS = {
    1: "硬科技抢验数据线 —— 全站自研、存算一体、端到端驱动成为新主流",
    2: "宁德 / 京东 / 三甲已成参照 —— 入场券 = 节拍、误查率、合规",
    3: "嘉宾给出坐标而非答案 —— 机器狗 1-2 年、家用 3-5 年、AI 科研 1-3 年",
    4: "普惠曲线在所有赛道拐头 —— 3500 元灵巧手、1/4 价减速器、机器人 10 万 → 3 万",
}

DIR_SUBS = {
    1: "处在什么阶段？用什么量化指标判定，不是概念。",
    2: "不要 PPT，要客户名 + 准确率 + 节拍数据。",
    3: "什么技术什么时候能到什么程度？给一个时间锚。",
    4: "技术能不能普惠，让更多人、中小企业、文科生都用上。",
}


def classify_to_dir(theme_name: str, body: str) -> int:
    """根据主题名+正文，返回 4 方向里最匹配的方向（1-4）"""
    text = theme_name + " " + body[:80]
    best = 1
    best_score = 0
    for d, (_, kws) in DIR_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in text)
        if score > best_score:
            best_score = score
            best = d
    return best


def one_liner(text: str, max_len: int = 16) -> str:
    """提取首句核心短语，限长 max_len 字（中文按字计）。"""
    # 切到首个句末标点
    first = re.split(r"[。；，]", text, maxsplit=1)[0]
    # 去掉"比如/例如/以及"等连接词开头的啰嗦
    first = re.sub(r"^(比如|例如|以及|具体|具体来说|主要是|主要做|主打)[：:，,、]?", "", first)
    if len(first) > max_len:
        return first[:max_len]
    return first


def parse_qa_for_dashboard(qa_path: Path) -> list[dict]:
    """读 QA 文件 → 每家公司按 4 方向聚类，每方向最多一句话（≤16 字）。"""
    text = qa_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    SECTION_RE = re.compile(r"^##\s+访谈(.+?)：(.+?)\s*$")
    A_LINE_RE = re.compile(r"^-\s+\*\*(.+?)\*\*[：:]\s*(.+)$")

    companies: list[dict] = []
    current: dict | None = None
    in_answer = False
    for ln in lines:
        m = SECTION_RE.match(ln)
        if m:
            if current:
                companies.append(current)
            current = {
                "company": m.group(2).strip(),
                "desc": "",
                "dirs": {1: "", 2: "", 3: "", 4: ""},
            }
            in_answer = False
            continue
        if current is None:
            continue
        if ln.strip().startswith("### 回答摘要"):
            in_answer = True
            continue
        if ln.startswith("## "):
            in_answer = False
        if in_answer:
            am = A_LINE_RE.match(ln.strip())
            if am:
                theme = am.group(1).strip()
                body = am.group(2).strip()
                short = one_liner(body, 18)
                if not short:
                    continue
                d = classify_to_dir(theme, body)
                # 该方向上第一次出现 → 写入；否则不覆盖（保留更短/更早的）
                if not current["dirs"][d]:
                    current["dirs"][d] = short
                if not current["desc"]:
                    current["desc"] = one_liner(theme, 10)

    if current:
        companies.append(current)
    return companies


def parse_mece_for_question_list(mece_path: Path) -> dict:
    """读 18 号 MECE（含 🆕/♻️ 标记）→ 按 13 大类分组的 question list"""
    text = mece_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    categories: list[dict] = []
    current_cat: dict | None = None
    current_sub: dict | None = None
    counter_in_sub = 0

    Q_LINE_NEW = re.compile(r'^- 🆕 "(.+?)"(?:\s*_\(对照17号同类："(.+?)"\)_)?\s*—\s*_(.+?)_\s*$')
    Q_LINE_EVOLVE = re.compile(r'^- ⟳ "(.+?)"(?:\s*_\(对照17号同类："(.+?)"\)_)?\s*—\s*_(.+?)_\s*$')
    Q_LINE_SAME = re.compile(r'^- ✓ "(.+?)"(?:\s*_\(对照17号同类："(.+?)"\)_)?\s*—\s*_(.+?)_\s*$')
    Q_LINE_NEW_NO_REF = re.compile(r'^- 🆕 "(.+?)"\s*—\s*_(.+?)_\s*$')
    Q_LINE_EVOLVE_NO_REF = re.compile(r'^- ⟳ "(.+?)"\s*—\s*_(.+?)_\s*$')
    Q_LINE_SAME_NO_REF = re.compile(r'^- ✓ "(.+?)"\s*—\s*_(.+?)_\s*$')
    CAT_RE = re.compile(r"^##\s+(.+)$")
    SUB_RE = re.compile(r"^###\s+\d+\.\s+(.+)$")

    for ln in lines:
        m_cat = CAT_RE.match(ln)
        if m_cat and not ln.startswith("###"):
            if current_sub and current_cat:
                if current_sub["questions"]:
                    current_cat["subs"].append(current_sub)
            if current_cat:
                categories.append(current_cat)
            current_cat = {"title": m_cat.group(1).strip(), "subs": [], "meta": ""}
            current_sub = None
            continue
        m_sub = SUB_RE.match(ln)
        if m_sub:
            if current_sub and current_cat and current_sub["questions"]:
                current_cat["subs"].append(current_sub)
            current_sub = {"name": m_sub.group(1).strip(), "questions": []}
            counter_in_sub = 0
            continue

        if current_sub is None:
            continue

        for pattern, tag, marker in [
            (Q_LINE_NEW, "new", "🆕"),
            (Q_LINE_EVOLVE, "evolve", "⟳"),
            (Q_LINE_SAME, "same", "✓"),
            (Q_LINE_NEW_NO_REF, "new", "🆕"),
            (Q_LINE_EVOLVE_NO_REF, "evolve", "⟳"),
            (Q_LINE_SAME_NO_REF, "same", "✓"),
        ]:
            m = pattern.match(ln)
            if m:
                counter_in_sub += 1
                if len(m.groups()) == 3:
                    text_q, _, source = m.groups()
                else:
                    text_q, source = m.groups()
                current_sub["questions"].append({
                    "text": text_q,
                    "source": source,
                    "tag": tag,
                    "marker": marker,
                })
                break

    if current_sub and current_cat and current_sub["questions"]:
        current_cat["subs"].append(current_sub)
    if current_cat:
        categories.append(current_cat)

    return {"categories": categories}
    """判断是否是完整句子而非问题名（含动词"访谈/介绍/分享"或 >18 字）"""
    if len(text) > 18:
        return True
    if any(p in text for p in ["，", "。", "？", "！", "、", "（", "）"]):
        return True
    return bool(re.search(r"(访谈|介绍|分享|讲述|谈到|聊到)", text))


def is_sentence_like(text: str) -> bool:
    """判断是否是完整句子而非问题名（含动词"访谈/介绍/分享"或 >20 字）"""
    if len(text) > 20:
        return True
    if any(p in text for p in ["，", "。", "？", "！", "、", "（", "）"]):
        return True
    return bool(re.search(r"(访谈|介绍|分享|讲述|谈到|聊到)", text))


def filter_noise(categories: list[dict]) -> list[dict]:
    """过滤句子型主题 + 跳过空类目"""
    out = []
    for cat in categories:
        new_subs = []
        for sub in cat["subs"]:
            new_qs = [q for q in sub["questions"] if not is_sentence_like(q["text"])]
            if new_qs:
                sub["questions"] = new_qs
                new_subs.append(sub)
        if new_subs:
            cat["subs"] = new_subs
            out.append(cat)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", default="2026-07-18")
    args = parser.parse_args()

    qa_path = REPO_ROOT / "2-processing" / "2026" / "0718" / "07月18日WAIC流水席对话录：提问与回答摘要.md"
    mece_path = REPO_ROOT / "2-processing" / "2026" / "0718" / "07月18日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md"

    if not qa_path.exists() or not mece_path.exists():
        print("ERROR: 18 号 QA/MECE 文件缺失", file=sys.stderr)
        return 1

    companies = parse_qa_for_dashboard(qa_path)
    mece = parse_mece_for_question_list(mece_path)
    print(f"✓ 解析 {len(companies)} 家公司 × 4 方向")
    print(f"✓ 解析 {sum(len(c['subs']) for c in mece['categories'])} 个子类")

    # 过滤噪声（句子型主题 + 空类目）
    mece["categories"] = filter_noise(mece["categories"])

    new_count = sum(1 for cat in mece["categories"] for sub in cat["subs"] for q in sub["questions"] if q["tag"] == "new")

    # 准备 dashboard 数据
    directions = []
    for d in (1, 2, 3, 4):
        name = DIR_KEYWORDS[d][0]
        directions.append({
            "title": name,
            "sub": DIR_SUBS[d],
            "quotes": DIR_QUOTES[d],
            "answer": DIR_ANSWERS[d],
            "takeaway": DIR_TAKEAWAYS[d],
        })

    rows = []
    for c in companies:
        rows.append({
            "company": c["company"],
            "desc": c["desc"][:20] if c["desc"] else "",
            "c1": c["dirs"][1],
            "c2": c["dirs"][2],
            "c3": c["dirs"][3],
            "c4": c["dirs"][4],
        })

    # 准备问题清单数据
    total_q = sum(1 for cat in mece["categories"] for sub in cat["subs"] for _ in sub["questions"])

    # Jinja2 + Playwright
    jinja_env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    out_dir = REPO_ROOT / "3-outputs" / "2026" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    dash_path = out_dir / f"{args.day.replace('-', '')[4:]}-dashboard.png"
    ql_path = out_dir / f"{args.day.replace('-', '')[4:]}-question-list.png"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()

        # ====== 1. 看板图（横向 1920×1200）======
        ctx1 = browser.new_context(viewport={"width": 1920, "height": 1200}, device_scale_factor=2)
        page1 = ctx1.new_page()
        tmpl = jinja_env.get_template("dashboard.html")
        html = tmpl.render(
            day=args.day,
            interview_count=len(companies),
            new_count=new_count,
            sub=f"核心结论：18 号 {len(companies)} 场访谈，主持人用 4 类问题线去对应每家公司的不同方向——技术路线 / 落地场景 / 时间表 / 成本可及性。",
            directions=directions,
            rows=rows,
        )
        page1.set_content(html, wait_until="networkidle")
        page1.evaluate("document.fonts.ready")
        page1.screenshot(path=str(dash_path), full_page=True)
        print(f"✓ 看板 → {dash_path}")
        ctx1.close()

        # ====== 2. 问题清单长条（竖向 720×4400）======
        ctx2 = browser.new_context(viewport={"width": 720, "height": 4400}, device_scale_factor=2)
        page2 = ctx2.new_page()
        tmpl2 = jinja_env.get_template("question_list.html")
        html2 = tmpl2.render(
            day=args.day,
            total=total_q,
            categories=mece["categories"],
        )
        page2.set_content(html2, wait_until="networkidle")
        page2.evaluate("document.fonts.ready")
        page2.screenshot(path=str(ql_path), full_page=True)
        print(f"✓ 问题清单 → {ql_path}")
        ctx2.close()

        browser.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
