"""Diff 17 vs 18 MECE problem list and produce highlighted 18号 version.

Heuristic for "same problem":
  - Exact match: question name identical → ♻️ 已有
  - High Jaccard similarity on 2-char grams (≥0.6) → ♻️ 同类
  - Otherwise: 🆕 新增
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/Users/macos/Workspaces/AI/waic-getnote-open-debrief")
DAY1 = ROOT / "2-processing/2026/0717/07月17日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md"
DAY2 = ROOT / "2-processing/2026/0718/07月18日WAIC流水席：罗振宇与快刀青衣的提问清单（MECE分类）.md"
DAY2_OUT = DAY2  # 原地覆盖


def parse_questions_with_source(path: Path) -> list[tuple[str, str, int]]:
    """返回 [(问题名, 访谈引用, 行号), ...]，顺序保留。"""
    text = path.read_text(encoding="utf-8")
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r'-\s*"([^"]+?)"\s*—\s*_(.+?)_\s*$', line.strip())
        if m:
            out.append((m.group(1).strip(), m.group(2).strip(), i))
    return out


def bigrams(s: str) -> set[str]:
    """提取 2 字 grams"""
    s = re.sub(r"[：:、，,。.\s（）()【】\[\]]", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_sentence_like(q: str) -> bool:
    """主题名是否看起来像完整句子（含动词"访谈/介绍/分享/讲述/访谈"等）"""
    # 含逗号、句号、问号、感叹号、或长主题名（>20 字）
    if len(q) > 20:
        return True
    if any(p in q for p in ["，", "。", "？", "！", "、"]):
        return True
    # 含"访谈/介绍/分享"等动作描述词
    return bool(re.search(r"(访谈|介绍|分享|讲述|谈到|聊到)", q))


def diff_label(q: str, day1_questions: list[tuple[str, str, int]]) -> tuple[str, str | None]:
    """返回 (emoji, 匹配的17号问题或None)

    三分类：
      - "NEW"   (🆕)  = 17 号完全没问过
      - "EVOLVE" (⟳) = 17 号有同类，但问法/角度有变（Jaccard 0.5-1）
      - "SAME"  (✓)  = 完全相同
    """
    # 排除"句子型"主题（实际是章节概要混入的，不是真问题）
    if is_sentence_like(q):
        return "🆕", None

    q_grams = bigrams(q)
    # 1) 精确匹配
    for d1_q, _, _ in day1_questions:
        if d1_q == q:
            return "✓", d1_q
    # 2) Jaccard 相似度
    best = ("🆕", None)
    best_sim = 0.0
    for d1_q, _, _ in day1_questions:
        if is_sentence_like(d1_q):
            continue
        sim = jaccard(q_grams, bigrams(d1_q))
        if sim > best_sim:
            best_sim = sim
            best = ("⟳" if sim >= 0.5 else "🆕", d1_q)
    return best


def main():
    day1 = parse_questions_with_source(DAY1)
    day2 = parse_questions_with_source(DAY2)
    print(f"17 号问题数: {len(day1)}")
    print(f"18 号问题数: {len(day2)}")

    # 替换 18 号每行 — 加上 emoji（保留原引用）
    lines = DAY2.read_text(encoding="utf-8").splitlines()
    new_lines = list(lines)
    counter = {"✓": 0, "⟳": 0, "🆕": 0}
    for q, src, ln in day2:
        emoji, matched = diff_label(q, day1)
        counter[emoji] += 1
        old_line = new_lines[ln - 1]
        if matched and matched != q:
            inject = f'{emoji} "{q}" _(对照17号同类："{matched}")_'
        else:
            inject = f'{emoji} "{q}"'
        new_line = old_line.replace(f'"{q}"', inject, 1)
        new_lines[ln - 1] = new_line

    # 在文件顶部加对比说明
    summary = (
        "\n> ## 🔍 17 号 vs 18 号 MECE 对比（三色分类）\n"
        f"> 18 号共 {len(day2)} 个问题：🆕 新增 {counter['🆕']} 个 / ⟳ 进化 {counter['⟳']} 个 / ✓ 相同 {counter['✓']} 个。\n"
        f"> 判别规则：主题名完全相同 = ✓ 相同；Jaccard 相似度 ≥ 0.5 = ⟳ 进化（同类但角度变）；否则 = 🆕 新增。\n\n"
    )
    # 插在 frontmatter 之后第一个 > 引用之后
    insert_idx = None
    for i, line in enumerate(new_lines):
        if line.startswith("# ") and "WAIC 流水席" in line:
            insert_idx = i + 1
            break
    if insert_idx is not None:
        new_lines.insert(insert_idx, summary.rstrip())

    DAY2_OUT.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"\n✓ 相同: {counter['✓']}")
    print(f"⟳ 进化: {counter['⟳']}")
    print(f"🆕 新增: {counter['🆕']}")
    print(f"✅ 写回 {DAY2_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
