"""Build 17/18号 Q&A + MECE markdown from the 4-group source transcripts.

Reads: 1-data/2026/05 罗振宇.../WAIC流水席/*.md (4 files)
Writes: 2-processing/2026/0717/*.md  (Q&A + MECE)
        2-processing/2026/0718/*.md  (Q&A + MECE)

Each output file has frontmatter + a body driven by 6 MECE categories
defined below (MECE = Mutually Exclusive, Collectively Exhaustive).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path("/Users/macos/Workspaces/AI/waic-getnote-open-debrief")
SRC_DIR = REPO / "1-data" / "2026" / "05 罗振宇、快刀青衣WAIC直播精华" / "WAIC流水席"

# 文件 -> 组
GROUP_FILES = {
    1: SRC_DIR / "WAIC流水席第1组嘉宾：云深处、千寻、交泰、绳肌妙算、陶世、永轴智造等.md",
    2: SRC_DIR / "WAIC流水席第2组嘉宾：奇岱松、松应科技、香港大学、凌迪科技等.md",
    3: SRC_DIR / "WAIC流水席第3组嘉宾：开普勒、灵漾AI、灵动世界、猿声先达等.md",
    4: SRC_DIR / "WAIC流水席第4组嘉宾：上海音乐学院、灵初智能、国华智能、加速进化等.md",
}

# 17 号 = 第 1+2 组；18 号 = 第 3+4 组
DAY_TO_GROUPS = {
    "2026-07-17": [1, 2],
    "2026-07-18": [3, 4],
}

# === 老格式 MECE 13 大类（对齐 07月17日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md）===
# 顺序固定，结构固定。每个大类下若干子类。
MECE_CATEGORIES = [
    ("一、开场与定位类问题", [
        ("产品定位问题", ["公司", "产品定位", "核心业务", "业务定位", "核心功能", "诞生背景", "团队", "公司业务"]),
        ("现状评估问题", ["做到什么", "做到什么程度", "目前进展", "落地", "现状"]),
    ]),
    ("二、行业影响与变化类问题", [
        ("AI带来的行业变化", ["AI", "行业", "变化", "渗透", "改变"]),
    ]),
    ("三、未来展望类问题", [
        ("未来期待与规划", ["未来", "规划", "预判", "展望", "愿景", "终极形态", "发展目标", "时间预测"]),
    ]),
    ("四、技术细节与攻坚类问题", [
        ("技术路线选择", ["技术路线", "路线选择", "为什么选择"]),
        ("技术难点与突破", ["技术难点", "技术攻坚", "技术突破", "难点", "核心难点", "攻坚", "技术进展", "数据积累", "技术特点", "技术优势"]),
    ]),
    ("五、落地场景与案例类问题", [
        ("具体应用场景", ["应用场景", "场景", "实际场景", "使用场景"]),
        ("落地进展与效果", ["落地案例", "落地进展", "客户落地", "落地效果", "应用案例"]),
    ]),
    ("六、成本与商业模式类问题", [
        ("成本控制与定价", ["定价", "价格", "成本", "降本", "免费版本"]),
        ("商业模式与盈利", ["商业模式", "盈利", "客户群体", "客户分布", "营收"]),
    ]),
    ("七、行业竞争与优势类问题", [
        ("竞争优势", ["竞争优势", "核心竞争力", "核心优势", "差异化", "独特"]),
        ("行业地位", ["行业地位", "排名", "行业进展", "行业判断", "行业洞察"]),
    ]),
    ("八、用户与市场类问题", [
        ("用户群体变化", ["用户群体", "用户画像", "用户分布", "用户变化", "用户反馈"]),
        ("市场前景判断", ["市场前景", "市场规模", "市场空间", "爆发", "需求"]),
    ]),
    ("九、入行建议与人才类问题", [
        ("入行门槛与建议", ["入行", "入门", "人才", "建议", "文科生", "选专业"]),
    ]),
    ("十、跨领域关联类问题", [
        ("技术关联与融合", ["融合", "关联", "跨领域", "AI for"]),
        ("产业链协同", ["产业链", "上下游", "配套", "供应商", "生态"]),
    ]),
    ("十一、社会影响与价值类问题", [
        ("社会价值", ["社会", "价值", "意义", "普惠", "公共"]),
        ("行业变革意义", ["变革", "颠覆", "推动", "改变行业", "里程碑"]),
    ]),
    ("十二、个人体验与感受类问题", [
        ("逛展感受", ["逛展", "WAIC变化", "大会感受", "印象"]),
        ("产品体验", ["体验", "使用感受", "用起来"]),
    ]),
    ("十三、推荐与建议类问题", [
        ("产品推荐", ["推荐", "选择", "大模型推荐"]),
        ("行业建议", ["建议给", "对想"]),
    ]),
]


def categorize(theme_name: str) -> tuple[str, str]:
    """把子主题名映射到 (大类名, 子类名)。返回最佳匹配。"""
    best = None
    best_score = 0
    for cat_name, subcats in MECE_CATEGORIES:
        for sub_name, keywords in subcats:
            for kw in keywords:
                if kw in theme_name:
                    score = len(kw)
                    if score > best_score:
                        best = (cat_name, sub_name, theme_name)
                        best_score = score
    if best:
        return best[0], best[1]
    return "五、行业洞察与趋势判断", "未来期待与规划"  # 默认兜底


_CN = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
       "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
       "二十一", "二十二", "二十三", "二十四", "二十五", "二十六", "二十七", "二十八", "二十九", "三十"]


def cn(n: int) -> str:
    if 0 <= n < len(_CN):
        return _CN[n]
    return str(n)


def parse_source(md_path: Path) -> tuple[str, list[dict]]:
    """Parse one source file → (ai_summary_text, list of interviews).

    Each interview: {"title": str, "themes": [{"name": str, "body": str}, ...]}

    Supports two formats:
    - 第 1 组: 段标题 `**xxx**`, 子主题 `* **xxx**: content`
    - 第 2/3/4 组: 段标题 `xxx`, 子主题 `xxx: content`

    严格规则：只解析智能总结里的访谈块（段标题 + 子主题）；章节概要 / 金句 / 待办 / 录音总结 / 录音信息 全部跳过。
    """
    text = md_path.read_text(encoding="utf-8")
    body = text.split("# 文字稿", 1)[0]
    # 不管有没有 📑 智能总结：直接在 body 里找段标题起点
    # 关键启发式：
    #   段标题是 "独占一行" 的文本
    #   第 1 组: `**xxx**`
    #   第 2/3/4 组: `xxx分享/介绍/访谈...` (短文本，含关键词)

    # 跳到智能总结后，但保留 markdown 结构（行级别）
    if "📑 智能总结" in body:
        body = body.split("📑 智能总结", 1)[1]
    # 跳过智能总结后的章节概要 / 金句 / 待办
    for marker in ("### 📅 章节概要", "### ✨ 金句精选", "### 📋 待办事项"):
        if marker in body:
            body = body.split(marker, 1)[0]
    body = re.sub(r"^###.*\n", "", body, count=1, flags=re.MULTILINE)

    # 不再做行级别过滤；直接进入段标题识别
    # 用 starts 标记：遇到第一个段标题之前的内容全部丢弃

    lines = body.splitlines()

    interviews: list[dict] = []
    current: dict | None = None
    pending_title: str | None = None
    pending_intro: list[str] = []

    def flush_title():
        nonlocal pending_title, pending_intro, current
        if pending_title:
            current = {"title": pending_title.strip(), "intro": " ".join(pending_intro).strip(), "themes": []}
            interviews.append(current)
            pending_title = None
            pending_intro = []

    def looks_like_interview_title(s: str) -> bool:
        """判断一行文本是否是访谈段标题。
        第 1 组: **xxx**（带粗体）—— 由调用方在 m2 中专门处理。
        第 2/3/4 组: 纯文本，特征是"以公司名开头 + 含分享/介绍/访谈等关键词 + 不含句子标点 + 短"。
        """
        s = s.strip()
        if not (4 <= len(s) <= 40):
            return False
        if s.startswith(("#", "*", "-", "•", "http")):
            return False
        if any(p in s for p in ["。", "？", "！", "，", "；", "（", "）"]):
            return False
        # 元数据关键词排除（智能总结开头的"内容类型"/"录音总结"/"时长"等）
        meta_kw = ("内容类型", "录音信息", "录音总结", "时长", "参与人数", "本次访谈", "本次录音",
                   "00:00", "00:0", "00:1", "00:2", "00:3", "00:4", "00:5", "00:6", "00:7",
                   "00:8", "00:9", "01:0", "01:1", "01:2", "01:3", "01:4", "01:5", "01:6",
                   "01:7", "01:8", "01:9", "02:", "03:", "04:", "05:")
        if any(kw in s for kw in meta_kw):
            return False
        # 必须有"分享/介绍/访谈"等访谈信号词
        sig = ("分享", "介绍", "访谈", "案例", "概览", "播报",
               "产品介绍", "业务", "技术", "公司", "科技", "智能", "机器人")
        return any(kw in s for kw in sig)

    # 元数据/标题候选行（含"分享/介绍"等）
    candidate_title_lines = []

    # 第 1 步：找出所有"段标题候选"的位置
    for idx, ln in enumerate(lines):
        stripped = ln.strip()
        if re.match(r"^\*\*[^*]+\*\*\s*$", stripped):
            # 第 1 组格式
            m = re.match(r"^\*\*([^*]+?)\*\*\s*$", stripped)
            candidate_title_lines.append((idx, m.group(1).strip()))
        elif looks_like_interview_title(stripped):
            # 第 2/3/4 组格式
            candidate_title_lines.append((idx, stripped))

    # 第 2 步：每个候选行"向前找最近的智能总结内元数据结束点"，用第一个候选作为起点
    # 简化：取第一个候选作为起点
    if not candidate_title_lines:
        return body, []

    start_line = candidate_title_lines[0][0]
    body_lines = lines[start_line:]

    # 第 3 步：从 body_lines 重新解析
    interviews = []
    current = None
    pending_title = None
    pending_intro = []

    def flush_title():
        nonlocal pending_title, pending_intro, current
        if pending_title:
            current = {"title": pending_title.strip(), "intro": " ".join(pending_intro).strip(), "themes": []}
            interviews.append(current)
            pending_title = None
            pending_intro = []

    i = 0
    while i < len(body_lines):
        ln = body_lines[i].rstrip()
        if not ln.strip():
            i += 1
            continue

        # 第 1 组主题块
        m1 = re.match(r"^\*\s+\*\*([^*]+?)\*\*[：:]\s*(.+)$", ln)
        if m1:
            if pending_title:
                flush_title()
            if current is None:
                i += 1; continue
            current["themes"].append({"name": m1.group(1).strip(), "body": m1.group(2).strip()})
            i += 1
            continue

        # 第 1 组段标题
        m2 = re.match(r"^\*\*([^*]+?)\*\*\s*$", ln)
        if m2:
            if pending_title:
                flush_title()
            elif current and current["themes"]:
                current = None
            pending_title = m2.group(1).strip()
            pending_intro = []
            i += 1
            continue

        # 第 2/3/4 组主题块：xxx：yyy 形式
        m3 = re.match(r"^([^：:\n]{2,30})[：:]\s*(.+)$", ln)
        if m3 and not ln.startswith(("http", "📑", "###", "**", "* ")):
            name = m3.group(1).strip()
            body_text = m3.group(2).strip()
            is_sentence_like = any(p in name for p in ["。", "，", "是", "了", "在", "？", "！"])
            # 先看是否是段标题（含分享/介绍/访谈等关键词的"长标题"）
            if current is None and not is_sentence_like and looks_like_interview_title(ln.strip()):
                if pending_title:
                    flush_title()
                pending_title = ln.strip()
                pending_intro = []
                i += 1
                continue
            # 否则是当前访谈的子主题；先 flush pending 创建 current
            if pending_title:
                flush_title()
            if current is None:
                i += 1; continue
            current["themes"].append({"name": name, "body": body_text})
            i += 1
            continue

        # 第 2/3/4 组段标题（纯文本，独占一行）
        if looks_like_interview_title(ln):
            if pending_title:
                flush_title()
            elif current and current["themes"]:
                current = None
            pending_title = ln.strip()
            pending_intro = []
            i += 1
            continue

        # 简介
        if pending_title:
            pending_intro.append(ln)
        elif current and not current["themes"]:
            current["intro"] = (current["intro"] + " " + ln).strip()
        # 其他情况忽略（避免元数据污染）
        i += 1

    if pending_title:
        flush_title()

    return body, [iv for iv in interviews if iv["themes"]]

    if pending_title:
        flush_title()

    return body, [iv for iv in interviews if iv["themes"]]


# ====== 过滤直播主持人记录 ======
HOST_NOISE_PATTERNS = [
    "邀请", "入场", "刀哥访谈", "罗老师访谈", "罗老师介绍",
    "所有中奖用户", "抽奖", "得到大脑的核心", "按照固定", "产品组合内容",
]


def extract_company_name(title: str) -> str:
    """从访谈标题提取核心公司名（短版：前 2-4 字 + 全名）"""
    # 去掉前缀数字（"01-XXX"）
    title = re.sub(r"^\d+-", "", title)
    # 切到第一个（之前
    for sep in ["（", "(", "【", "「"]:
        if sep in title:
            title = title.split(sep, 1)[0]
            break
    # 去掉"访谈"/"分享"等后缀
    title = re.sub(r"(访谈|分享|案例|介绍)$", "", title)
    return title.strip()


def company_aliases(company_full: str) -> set[str]:
    """生成公司名的多个别名（短/长），用于匹配主题名。"""
    aliases = {company_full}
    # 短别名：前 2-4 字
    for n in (2, 3, 4):
        if len(company_full) >= n:
            aliases.add(company_full[:n])
    # 去通用后缀（如"科技"）
    for suffix in ["科技", "智能", "公司"]:
        if company_full.endswith(suffix):
            aliases.add(company_full[:-len(suffix)])
    return aliases


def is_host_noise(theme: str, body: str = "", current_title: str = "", all_aliases: set[str] = None, current_aliases: set[str] = None) -> bool:
    """识别"直播主持人记录"（时间戳/转场/抽奖等）而非真问题。"""
    text = theme + " " + body
    if any(p in text for p in HOST_NOISE_PATTERNS):
        return True
    # 纯数字主题（如"00"、"01"）通常是时间戳
    if re.fullmatch(r"[\d\s.,:：\-—]+", theme):
        return True
    # 短主题名（≤6 字）且匹配其他访谈的公司别名 → 过滤
    if all_aliases and len(theme) <= 6:
        for alias in all_aliases:
            if not alias or alias in (current_aliases or set()):
                continue
            if alias == theme or alias in theme:
                return True
    return False


def filter_host_noise(interviews: list[dict]) -> list[dict]:
    """过滤所有访谈里的"直播主持人记录"主题。"""
    all_aliases: set[str] = set()
    iv_company_map: dict[int, set[str]] = {}
    for iv in interviews:
        c = extract_company_name(iv["title"])
        aliases = company_aliases(c)
        all_aliases.update(aliases)
        iv_company_map[id(iv)] = aliases
    out = []
    for iv in interviews:
        current_aliases = iv_company_map[id(iv)]
        iv["themes"] = [
            th for th in iv["themes"]
            if not is_host_noise(th["name"], th.get("body", ""), iv["title"], all_aliases, current_aliases)
        ]
        out.append(iv)
    return out


def filter_host_noise(interviews: list[dict]) -> list[dict]:
    """过滤所有访谈里的"直播主持人记录"主题。"""
    all_titles = [iv["title"] for iv in interviews]
    out = []
    for iv in interviews:
        iv["themes"] = [
            th for th in iv["themes"]
            if not is_host_noise(th["name"], th.get("body", ""), iv["title"], all_titles)
        ]
        out.append(iv)
    return out

def build_qa_md(day: str, interviews: list[dict], group_label: str) -> str:
    """Generate Q&A markdown for a day."""
    fm = (
        "---\n"
        f'title: "{day} WAIC 流水席对话录：提问与回答摘要"\n'
        "author: Joe\n"
        f"date: {day}\n"
        f"source: getnote ({group_label} 完整文字稿)\n"
        "---\n\n"
    )
    parts = [fm, f"# {day} WAIC 流水席对话录：提问与回答摘要\n\n"]
    parts.append(f"> 基于{group_label}的 AI 智能总结主题块提取。每场访谈列：提问清单（子主题）+ 公司回答摘要。\n\n")
    parts.append("---\n\n")

    # 给每场加序号
    counter = 0
    for iv in interviews:
        # 跳过非公司类段（开场、活动、收尾、产品推广、章节概要残骸等）
        skip_kw = ["直播开场", "开场与理念", "活动安排", "收尾", "感悟",
                   "产品推广", "结束", "章节概要", "金句", "待办",
                   "内容类型", "录音信息", "录音总结", "抽奖", "展位",
                   "WAIC特刊主编", "主持开场"]
        if any(k in iv["title"] for k in skip_kw):
            continue
        counter += 1
        cn_num = cn(counter)
        parts.append(f"## 访谈{cn_num}：{iv['title']}\n\n")
        if iv["intro"]:
            parts.append(f"**访谈定位**：{iv['intro']}\n\n")
        # 提问清单
        parts.append(f"### 提问清单（{len(iv['themes'])} 个）\n\n")
        for j, th in enumerate(iv["themes"], 1):
            parts.append(f"{j:02d}. **{th['name']}**\n")
        parts.append("\n### 回答摘要\n\n")
        for th in iv["themes"]:
            parts.append(f"- **{th['name']}**：{th['body']}\n")
        parts.append("\n---\n\n")

    return "".join(parts)


def build_mece_md(day: str, interviews: list[dict], group_label: str) -> str:
    """Generate MECE classification matching the legacy 13-category format.

    Layout (matches 07月17日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md):
      ## 一、xxx类问题
      ### 1. 子问题名
      - "你在做什么产品？"
      - "你们公司是做什么的？"
    """
    fm = (
        "---\n"
        f'title: "{day} 罗振宇与快刀青衣的提问清单（MECE分类）"\n'
        "author: Joe\n"
        f"date: {day}\n"
        f"source: getnote ({group_label} 完整文字稿)\n"
        "method: MECE 13 大类（对齐 07月17日老格式）\n"
        "---\n\n"
    )
    parts = [fm, f"# {day} 罗振宇与快刀青衣的提问清单（MECE分类）\n\n"]
    parts.append(f"> 基于{group_label}的 AI 总结主题块反推。每个子主题 = 主持人问的一个问题。\n")
    parts.append(f"> 总访谈：{len([iv for iv in interviews if iv['themes']])} 场；总问题：{sum(len(iv['themes']) for iv in interviews)} 个。\n\n")
    parts.append("> 格式对齐老版「07月17日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md」：13 大类 × 每类下若干子类。\n\n")
    parts.append("---\n\n")

    # 聚合：(大类名, 子类名) -> [(主题名, 访谈引用), ...]
    buckets: dict[tuple[str, str], list[tuple[str, str]]] = {}
    company_counter = 0
    for iv in interviews:
        # 跳过非公司类段
        skip_kw = ["开场", "抽奖", "展位", "活动安排", "收尾", "感悟",
                   "产品推广", "结束", "章节概要", "金句", "待办", "内容类型", "录音信息", "录音总结"]
        if any(k in iv["title"] for k in skip_kw):
            continue
        if not iv["themes"]:
            continue
        company_counter += 1
        cn_num = cn(company_counter)
        for th in iv["themes"]:
            cat_name, sub_name = categorize(th["name"])
            key = (cat_name, sub_name)
            buckets.setdefault(key, []).append((th["name"], f"访谈{cn_num}：{iv['title']}"))

    # 按 MECE_CATEGORIES 的顺序输出
    for cat_name, subcats in MECE_CATEGORIES:
        parts.append(f"## {cat_name}\n\n")
        any_in_cat = False
        for j, (sub_name, _kw) in enumerate(subcats, 1):
            items = buckets.get((cat_name, sub_name), [])
            if not items:
                continue
            any_in_cat = True
            parts.append(f"### {j}. {sub_name}\n\n")
            # 去重主题名（同一类目下同名问题合并，保留首次来源）
            seen = set()
            unique = []
            for name, src in items:
                if name in seen:
                    continue
                seen.add(name)
                unique.append((name, src))
            for name, src in unique:
                parts.append(f"- \"{name}\" — _{src}_\n")
            parts.append("\n")
        if not any_in_cat:
            parts.append("_（该日期未出现此类问题）_\n\n")

    return "".join(parts)


def main():
    for day, groups in DAY_TO_GROUPS.items():
        all_interviews = []
        for g in groups:
            _, ivs = parse_source(GROUP_FILES[g])
            # 第 1 组里把 "AI行业未来趋势预判" 等算访谈; 过滤无主题的段
            ivs = [iv for iv in ivs if iv["themes"]]
            # 过滤直播主持人记录（"邀请/刀哥访谈/罗老师访谈/00/01"等）
            ivs = filter_host_noise(ivs)
            all_interviews.extend(ivs)

        group_label = " + ".join(f"第{g}组" for g in groups)
        day_short = "0717" if day == "2026-07-17" else "0718"
        out_dir = REPO / "2-processing" / "2026" / day_short

        qa_path = out_dir / f"{day[5:].replace('-', '月')}日WAIC流水席对话录：提问与回答摘要.md"
        mece_path = out_dir / f"{day[5:].replace('-', '月')}日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md"

        qa_path.write_text(build_qa_md(day, all_interviews, group_label), encoding="utf-8")
        mece_path.write_text(build_mece_md(day, all_interviews, group_label), encoding="utf-8")

        print(f"✓ {day} ({group_label}): {len(all_interviews)} interviews")
        print(f"   QA:   {qa_path.relative_to(REPO)}  ({qa_path.stat().st_size} bytes)")
        print(f"   MECE: {mece_path.relative_to(REPO)}  ({mece_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
