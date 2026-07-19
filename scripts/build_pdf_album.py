"""Build a PDF album from 17号 + 18号 interview cards.

Output: 3-outputs/2026/figures/WAIC-2026-cards-album-0717-0718.pdf
Layout:
  Page 1: 封面（合集说明）
  Page 2-19: 17 号 18 张卡片
  Page 20-38: 18 号 19 张卡片
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path("/Users/macos/Workspaces/AI/waic-getnote-open-debrief")
OUT_PDF = REPO / "3-outputs/2026/figures/WAIC-2026-cards-album-0717-0718.pdf"
DIR_0717 = REPO / "3-outputs/2026/reports/0717"
DIR_0718 = REPO / "3-outputs/2026/reports/0718"


def list_cards(d: Path) -> list[Path]:
    return sorted(d.glob("*.png"))


def make_cover_page(w: int, h: int) -> Image.Image:
    """Generate cover page with title + sub-info."""
    img = Image.new("RGB", (w, h), (248, 246, 240))  # 米白底
    d = ImageDraw.Draw(img)

    # 字体
    def try_font(size: int):
        for fp in [
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            "/System/Library/Fonts/Hiragino Sans GB.ttc",
            "/Library/Fonts/Songti.ttc",
        ]:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
        return ImageFont.load_default()

    f_brand = try_font(60)
    f_title = try_font(80)
    f_sub = try_font(40)
    f_meta = try_font(28)
    f_small = try_font(22)

    # 顶部双色条
    d.rectangle([0, 0, int(w * 0.7), 28], fill=(31, 184, 197))   # teal
    d.rectangle([int(w * 0.7), 0, w, 28], fill=(184, 214, 48))   # lime

    # WAIC 标题
    d.text((120, 100), "WAIC 2026", font=f_brand, fill=(31, 184, 197))
    d.text((120, 180), "下午流水席访谈", font=f_brand, fill=(44, 62, 80))

    # 主标题
    title_y = 380
    d.text((120, title_y), "AI 二阶解读", font=f_title, fill=(44, 62, 80))
    d.text((120, title_y + 110), "访谈卡片合集", font=f_title, fill=(31, 184, 197))

    # 副信息
    sub_y = title_y + 280
    d.text((120, sub_y), "17 号 + 18 号   共 37 场访谈", font=f_sub, fill=(80, 80, 80))
    d.text((120, sub_y + 70), "来源：得到 App「得到大脑」", font=f_sub, fill=(80, 80, 80))
    d.text((120, sub_y + 140), "整理：Joe  ·  整理日期：2026-07-19", font=f_meta, fill=(120, 120, 120))

    # 仓库地址（真实地址）
    repo_y = sub_y + 280
    d.text((120, repo_y), "GitHub 仓库：", font=f_meta, fill=(80, 80, 80))
    d.text((120, repo_y + 50), "https://github.com/SS-13/waic-getnote-open-debrief", font=f_small, fill=(37, 99, 235))

    # 底部致谢
    thanks_y = h - 200
    d.text((120, thanks_y), "🙏 特别致谢", font=f_sub, fill=(184, 134, 11))
    d.text((120, thanks_y + 60), "本档案所有访谈内容，均来自得到 App「得到大脑」独家整理", font=f_meta, fill=(80, 80, 80))
    d.text((120, thanks_y + 100), "没有得到团队的现场采访，这份二阶解读档案不存在。", font=f_meta, fill=(80, 80, 80))

    # 底部页脚
    d.text((w - 320, h - 60), "TECH INTERVIEW NOTES", font=f_small, fill=(160, 160, 160))

    return img


def main():
    cards_0717 = list_cards(DIR_0717)
    cards_0718 = list_cards(DIR_0718)
    print(f"17 号卡片: {len(cards_0717)}")
    print(f"18 号卡片: {len(cards_0718)}")
    if not cards_0717 or not cards_0718:
        print("ERROR: 缺卡片", file=sys.stderr)
        return 1

    # 第一张卡片决定页面尺寸
    first = Image.open(cards_0717[0])
    w, h = first.size
    print(f"页面尺寸: {w} x {h}")

    # 构造所有页面
    pages: list[Image.Image] = []
    pages.append(make_cover_page(w, h))
    for p in cards_0717:
        pages.append(Image.open(p).convert("RGB"))
    for p in cards_0718:
        pages.append(Image.open(p).convert("RGB"))
    print(f"总页数: {len(pages)}")

    # 写 PDF（PIL 自动合并多张图为多页）
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        str(OUT_PDF),
        "PDF",
        resolution=150,
        save_all=True,
        append_images=pages[1:],
    )
    print(f"✓ 写回 {OUT_PDF.relative_to(REPO)}  ({OUT_PDF.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
