#!/usr/bin/env python3
"""塔罗牌占卜 CLI 工具 — 为 Claude Code 设计的塔罗占卜系统
带有 Rich 终端可视化 + 韦特塔罗牌图片显示"""

import argparse
import hashlib
import json
import os
import random
import sys
import urllib.request
from datetime import datetime
from io import BytesIO

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_JSON = os.path.join(SCRIPT_DIR, "data", "cards.json")
IMG_CACHE = os.path.join(SCRIPT_DIR, "data", "img_cache")

# ── Rich 导入（优雅降级） ────────────────────────────────────────────────────

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.columns import Columns
    from rich.text import Text
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

console = Console(width=120) if HAS_RICH else None

# ── 韦特塔罗图片 URL ────────────────────────────────────────────────────────

WIKI = "https://upload.wikimedia.org/wikipedia/commons"
MAJOR_IMAGES = {
    0: f"{WIKI}/9/90/RWS_Tarot_00_Fool.jpg",
    1: f"{WIKI}/d/de/RWS_Tarot_01_Magician.jpg",
    2: f"{WIKI}/8/88/RWS_Tarot_02_High_Priestess.jpg",
    3: f"{WIKI}/d/d2/RWS_Tarot_03_Empress.jpg",
    4: f"{WIKI}/c/c3/RWS_Tarot_04_Emperor.jpg",
    5: f"{WIKI}/8/8d/RWS_Tarot_05_Hierophant.jpg",
    6: f"{WIKI}/3/3a/TheLovers.jpg",
    7: f"{WIKI}/9/9b/RWS_Tarot_07_Chariot.jpg",
    8: f"{WIKI}/f/f5/RWS_Tarot_08_Strength.jpg",
    9: f"{WIKI}/4/4d/RWS_Tarot_09_Hermit.jpg",
    10: f"{WIKI}/3/3c/RWS_Tarot_10_Wheel_of_Fortune.jpg",
    11: f"{WIKI}/e/e0/RWS_Tarot_11_Justice.jpg",
    12: f"{WIKI}/2/2b/RWS_Tarot_12_Hanged_Man.jpg",
    13: f"{WIKI}/d/d7/RWS_Tarot_13_Death.jpg",
    14: f"{WIKI}/f/f8/RWS_Tarot_14_Temperance.jpg",
    15: f"{WIKI}/5/55/RWS_Tarot_15_Devil.jpg",
    16: f"{WIKI}/5/53/RWS_Tarot_16_Tower.jpg",
    17: f"{WIKI}/d/db/RWS_Tarot_17_Star.jpg",
    18: f"{WIKI}/7/7f/RWS_Tarot_18_Moon.jpg",
    19: f"{WIKI}/1/17/RWS_Tarot_19_Sun.jpg",
    20: f"{WIKI}/d/dd/RWS_Tarot_20_Judgement.jpg",
    21: f"{WIKI}/f/ff/RWS_Tarot_21_World.jpg",
}

GH = "https://raw.githubusercontent.com/metabismuth/tarot-json/master/cards"
MINOR_PREFIX = {"wands": "w", "cups": "c", "swords": "s", "pentacles": "p"}


def get_image_url(card):
    """获取牌的图片 URL"""
    if card["type"] == "大阿尔卡那":
        return MAJOR_IMAGES.get(card.get("number"))
    suit_key = card.get("suit_key")
    num = card.get("number")
    if suit_key and num is not None:
        prefix = MINOR_PREFIX.get(suit_key)
        if prefix:
            return f"{GH}/{prefix}{num:02d}.jpg"
    return None


def download_image(url):
    """下载图片并缓存到本地"""
    if not url:
        return None
    os.makedirs(IMG_CACHE, exist_ok=True)
    cache_file = os.path.join(IMG_CACHE, hashlib.md5(url.encode()).hexdigest() + ".jpg")
    if os.path.exists(cache_file):
        return cache_file
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(cache_file, "wb") as f:
            f.write(data)
        return cache_file
    except Exception:
        return None


# ── 终端图片渲染（半块 Unicode） ─────────────────────────────────────────────

def _load_fonts():
    """加载中文字体，返回 (large, medium, small) 字体元组"""
    from PIL import ImageFont
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return (
                    ImageFont.truetype(fp, 38),
                    ImageFont.truetype(fp, 22),
                    ImageFont.truetype(fp, 17),
                )
            except Exception:
                continue
    default = ImageFont.load_default()
    return (default, default, default)


def _get_spread_layout(spread_type, n):
    """返回每张牌的 (col, row) 网格坐标，定义各牌阵的传统形状。
    坐标以网格单元为单位（1 单元 = 牌宽 + 间距）。"""

    if spread_type == "single" or spread_type == "yesno" or n == 1:
        return [(0, 0)]

    if spread_type == "three" or n == 3:
        # 一行三张
        return [(0, 0), (1, 0), (2, 0)]

    if spread_type == "cross":
        # 凯尔特十字：左侧十字 + 右侧权杖（从下到上）
        #
        #              [3过去]  [1现状]  [5可能]
        #                      [2挑战]           [10最终]
        #              [4潜意] [6近未来]          [ 9希望]
        #                                        [ 8外部]
        #                                        [ 7自我]
        return [
            (1, 0),   # 1 现状（中心）
            (1, 1),   # 2 挑战（中心下方，横跨）
            (0, 0),   # 3 潜意识基础（左上）
            (0, 2),   # 4 过去（左下）
            (2, 0),   # 5 可能的结果（右上十字）
            (1, 2),   # 6 近未来（中下）
            (3.5, 3), # 7 自我态度（权杖最下）
            (3.5, 2), # 8 外部环境
            (3.5, 1), # 9 希望与恐惧
            (3.5, 0), # 10 最终结果（权杖最上）
        ]

    if spread_type == "horseshoe":
        # 马蹄形 U 型：
        #  [1]              [7]
        #    [2]          [6]
        #      [3]  [4]  [5]
        return [
            (0, 0),    # 1 过去
            (0.5, 1),  # 2 现在
            (1, 2),    # 3 隐藏的影响
            (2, 2),    # 4 障碍
            (3, 2),    # 5 周围环境
            (3.5, 1),  # 6 建议
            (4, 0),    # 7 可能的结果
        ]

    if spread_type == "love":
        # 爱情牌阵：心形对称
        #     [1自己]  [2对方]
        #        [3关系]
        #     [4挑战]  [5建议]
        #        [6结果]
        return [
            (0, 0),    # 1 自己
            (1.5, 0),  # 2 对方
            (0.75, 1), # 3 关系现状
            (0, 2),    # 4 挑战
            (1.5, 2),  # 5 建议
            (0.75, 3), # 6 结果
        ]

    if spread_type == "career":
        # 事业牌阵：金字塔形
        #        [5前景]
        #     [3优势] [4建议]
        #  [1现状] [2挑战]
        return [
            (0, 2),    # 1 现状
            (1.5, 2),  # 2 挑战
            (0, 1),    # 3 优势
            (1.5, 1),  # 4 建议
            (0.75, 0), # 5 前景
        ]

    # 默认：自动网格排列
    cols = min(n, 5)
    return [(i % cols, i // cols) for i in range(n)]


def render_spread_image(drawn_cards, positions, title, question=None,
                        output_path=None, spread_type=None):
    """将牌阵渲染为一张组合 PNG 图片，按传统牌阵形状布局。"""
    if not HAS_PIL:
        return None

    from PIL import ImageDraw

    CARD_W, CARD_H = 220, 370
    CELL_W = CARD_W + 40      # 网格单元宽
    CELL_H = CARD_H + 100     # 网格单元高（含标签）
    MARGIN = 50
    HEADER_H = 150
    BG_COLOR = (10, 6, 18)
    GOLD = (212, 175, 55)
    CYAN = (0, 229, 255)
    CREAM = (245, 240, 225)
    RED = (255, 80, 80)
    GREEN = (80, 255, 120)
    BORDER_COLOR = (180, 150, 50)
    DIM = (120, 120, 120)

    n = len(drawn_cards)
    layout = _get_spread_layout(spread_type, n)

    # 计算画布尺寸
    max_col = max(c for c, r in layout)
    max_row = max(r for c, r in layout)
    img_w = int(MARGIN * 2 + (max_col + 1) * CELL_W)
    img_h = int(HEADER_H + (max_row + 1) * CELL_H + MARGIN)

    canvas = Image.new("RGB", (img_w, img_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    font_large, font_medium, font_small = _load_fonts()

    # ── 装饰线 ──
    draw.line([(MARGIN, HEADER_H - 15), (img_w - MARGIN, HEADER_H - 15)],
              fill=(60, 50, 30), width=1)

    # ── 标题区 ──
    draw.text((MARGIN, 18), title, fill=GOLD, font=font_large)
    y_cursor = 68
    if question:
        draw.text((MARGIN, y_cursor), f"{t('question_prefix')}{question}", fill=CREAM, font=font_medium)
        y_cursor += 32
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    draw.text((MARGIN, y_cursor), now, fill=DIM, font=font_small)

    # ── 画每张牌 ──
    for idx, (cd, pos) in enumerate(zip(drawn_cards, positions)):
        card = cd["card"]
        is_reversed = cd["reversed"]

        col, row = layout[idx]
        x = int(MARGIN + col * CELL_W)
        y = int(HEADER_H + row * CELL_H)

        # 金色边框
        draw.rectangle([x - 3, y - 3, x + CARD_W + 3, y + CARD_H + 3],
                        outline=BORDER_COLOR, width=2)

        # 加载牌面图片
        url = get_image_url(card)
        img_path = download_image(url)
        card_drawn = False
        if img_path:
            try:
                card_img = Image.open(img_path).convert("RGB")
                if is_reversed:
                    card_img = card_img.rotate(180)
                card_img = card_img.resize((CARD_W, CARD_H), Image.LANCZOS)
                canvas.paste(card_img, (x, y))
                card_drawn = True
            except Exception:
                pass
        if not card_drawn:
            draw.rectangle([x, y, x + CARD_W, y + CARD_H], fill=(30, 20, 50))
            draw.text((x + 50, y + 170), card["name"], fill=GOLD, font=font_medium)

        # ── 标签 ──
        label_y = y + CARD_H + 10
        orientation = t("reversed") if is_reversed else t("upright")
        orient_color = RED if is_reversed else GREEN

        draw.text((x, label_y), f"【{pos}】", fill=CYAN, font=font_medium)
        draw.text((x, label_y + 28), card["name"], fill=CREAM, font=font_medium)
        draw.text((x + 2, label_y + 56), orientation, fill=orient_color, font=font_small)

    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, "data", "spread_result.png")
    canvas.save(output_path, "PNG")
    return output_path


def show_image_window(image_path, title="塔罗占卜结果"):
    """用 tkinter 弹窗显示图片，跨平台通用"""
    if not HAS_PIL or not image_path:
        return
    try:
        import tkinter as tk
        from PIL import ImageTk

        img = Image.open(image_path)
        # 限制窗口最大尺寸，保持比例
        max_w, max_h = 1200, 900
        ratio = min(max_w / img.width, max_h / img.height, 1.0)
        if ratio < 1.0:
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)

        root = tk.Tk()
        root.title(title)
        root.configure(bg="#0a0612")
        tk_img = ImageTk.PhotoImage(img)
        label = tk.Label(root, image=tk_img, bg="#0a0612")
        label.pack()
        # 窗口居中
        root.update_idletasks()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        x = (sw - root.winfo_width()) // 2
        y = (sh - root.winfo_height()) // 2
        root.geometry(f"+{x}+{y}")
        root.mainloop()
    except Exception:
        pass  # tkinter 不可用时静默失败


# ── 牌阵定义 ─────────────────────────────────────────────────────────────────

SPREADS = {
    "single": {
        "name": "单牌",
        "description": "抽取一张牌，获得简洁直观的指引",
        "positions": ["指引"],
    },
    "three": {
        "name": "三牌阵",
        "description": "过去/现在/未来 — 时间线解读",
        "positions": ["过去", "现在", "未来"],
    },
    "cross": {
        "name": "凯尔特十字",
        "description": "经典十牌阵，全方位深度解读",
        "positions": [
            "现状", "挑战/障碍", "潜意识基础", "过去", "可能的结果",
            "近未来", "自我态度", "外部环境", "希望与恐惧", "最终结果",
        ],
    },
    "horseshoe": {
        "name": "马蹄形",
        "description": "七牌阵，从过去到未来的完整弧线",
        "positions": ["过去", "现在", "隐藏的影响", "障碍", "周围环境", "建议", "可能的结果"],
    },
    "love": {
        "name": "爱情牌阵",
        "description": "六牌阵，专注感情与关系解读",
        "positions": ["自己", "对方", "关系现状", "挑战", "建议", "结果"],
    },
    "career": {
        "name": "事业牌阵",
        "description": "五牌阵，事业与职业方向解读",
        "positions": ["现状", "挑战", "优势", "建议", "前景"],
    },
    "yesno": {
        "name": "是非牌阵",
        "description": "单牌，给出「是/否」倾向的回答",
        "positions": ["指引"],
    },
}

SUIT_NAMES = {
    "wands": ("权杖", "Wands", "火"),
    "cups": ("圣杯", "Cups", "水"),
    "swords": ("宝剑", "Swords", "风"),
    "pentacles": ("星币", "Pentacles", "土"),
}

# ── 多语言支持 ──────────────────────────────────────────────────────────────────

I18N = {
    "zh": {
        "upright": "正位 ↑",
        "reversed": "逆位 ↓",
        "question_prefix": "提问：",
        "spread_title": "塔罗占卜",
        "random_draw_1": "随机抽取 1 张牌",
        "random_draw_n": "随机抽取 {} 张牌",
        "card_nth": "第{}张",
        "guidance": "指引",
        "position_label": "位置{}：{}",
        "draw_result": "抽取结果",
        "keywords_label": "关键词：",
        "meaning_label": "牌义：",
        "yes_tendency": "倾向「是」 ✓",
        "no_tendency": "倾向「否」 ✗",
        "neutral_tendency": "中性 / 不明确 ○",
        "tendency_label": "占卜倾向：",
        "ask_claude": "请 Claude 为您解读以上牌面",
        "question_label": "问题：",
        "window_title": "塔罗占卜结果",
        "vis_image": "可视化图片",
        "spreads": {
            "single": {"name": "单牌", "desc": "抽取一张牌，获得简洁直观的指引",
                       "positions": ["指引"]},
            "three": {"name": "三牌阵", "desc": "过去/现在/未来 — 时间线解读",
                      "positions": ["过去", "现在", "未来"]},
            "cross": {"name": "凯尔特十字", "desc": "经典十牌阵，全方位深度解读",
                      "positions": ["现状", "挑战/障碍", "潜意识基础", "过去", "可能的结果",
                                    "近未来", "自我态度", "外部环境", "希望与恐惧", "最终结果"]},
            "horseshoe": {"name": "马蹄形", "desc": "七牌阵，从过去到未来的完整弧线",
                          "positions": ["过去", "现在", "隐藏的影响", "障碍", "周围环境", "建议", "可能的结果"]},
            "love": {"name": "爱情牌阵", "desc": "六牌阵，专注感情与关系解读",
                     "positions": ["自己", "对方", "关系现状", "挑战", "建议", "结果"]},
            "career": {"name": "事业牌阵", "desc": "五牌阵，事业与职业方向解读",
                       "positions": ["现状", "挑战", "优势", "建议", "前景"]},
            "yesno": {"name": "是非牌阵", "desc": "单牌，给出「是/否」倾向的回答",
                      "positions": ["指引"]},
        },
    },
    "en": {
        "upright": "Upright ↑",
        "reversed": "Reversed ↓",
        "question_prefix": "Question: ",
        "spread_title": "Tarot Reading",
        "random_draw_1": "Single Card Draw",
        "random_draw_n": "Drawing {} Cards",
        "card_nth": "Card {}",
        "guidance": "Guidance",
        "position_label": "Position {}: {}",
        "draw_result": "Draw Result",
        "keywords_label": "Keywords: ",
        "meaning_label": "Meaning: ",
        "yes_tendency": "Leans \"Yes\" ✓",
        "no_tendency": "Leans \"No\" ✗",
        "neutral_tendency": "Neutral / Unclear ○",
        "tendency_label": "Tendency: ",
        "ask_claude": "Ask Claude to interpret the cards above",
        "question_label": "Question: ",
        "window_title": "Tarot Reading Result",
        "vis_image": "Visualization",
        "spreads": {
            "single": {"name": "Single Card", "desc": "Draw one card for quick guidance",
                       "positions": ["Guidance"]},
            "three": {"name": "Three-Card", "desc": "Past / Present / Future timeline",
                      "positions": ["Past", "Present", "Future"]},
            "cross": {"name": "Celtic Cross", "desc": "Classic 10-card in-depth reading",
                      "positions": ["Present", "Challenge", "Subconscious", "Past", "Potential",
                                    "Near Future", "Self", "Environment", "Hopes & Fears", "Outcome"]},
            "horseshoe": {"name": "Horseshoe", "desc": "7-card arc from past to future",
                          "positions": ["Past", "Present", "Hidden Influence", "Obstacle", "Surroundings", "Advice", "Potential"]},
            "love": {"name": "Love Spread", "desc": "6-card relationship reading",
                     "positions": ["Self", "Partner", "Relationship", "Challenge", "Advice", "Outcome"]},
            "career": {"name": "Career Spread", "desc": "5-card career guidance",
                       "positions": ["Current", "Challenge", "Strength", "Advice", "Prospect"]},
            "yesno": {"name": "Yes/No", "desc": "Single card yes/no tendency",
                      "positions": ["Guidance"]},
        },
    },
}

# Active language (default: zh, can be overridden by --lang)
_LANG = "zh"


def t(key):
    """Get translated string for current language."""
    return I18N.get(_LANG, I18N["zh"]).get(key, I18N["zh"].get(key, key))


def get_spread_i18n(spread_type):
    """Get spread info for current language."""
    lang_spreads = I18N.get(_LANG, I18N["zh"])["spreads"]
    return lang_spreads.get(spread_type, I18N["zh"]["spreads"].get(spread_type))

MAJOR_YESNO = {
    0: "yes", 1: "yes", 2: "neutral", 3: "yes", 4: "yes",
    5: "neutral", 6: "yes", 7: "yes", 8: "yes", 9: "neutral",
    10: "yes", 11: "yes", 12: "neutral", 13: "no", 14: "yes",
    15: "no", 16: "no", 17: "yes", 18: "no", 19: "yes",
    20: "yes", 21: "yes",
}


# ── 数据加载 ──────────────────────────────────────────────────────────────────

def load_cards():
    if not os.path.exists(CARDS_JSON):
        print(f"错误：找不到牌数据文件 {CARDS_JSON}")
        sys.exit(1)
    try:
        with open(CARDS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误：cards.json 格式不正确 — {e}")
        sys.exit(1)

    cards = []
    for card in data.get("major_arcana", []):
        cards.append({
            "name": card["name_cn"],
            "name_en": card["name"],
            "type": "大阿尔卡那",
            "number": card.get("number"),
            "suit_key": None,
            "keywords_upright": card["keywords_upright"],
            "keywords_reversed": card["keywords_reversed"],
            "upright_meaning": card.get("upright_meaning", ""),
            "reversed_meaning": card.get("reversed_meaning", ""),
            "yesno": MAJOR_YESNO.get(card.get("number", -1), "neutral"),
        })

    for suit_key, card_list in data.get("minor_arcana", {}).items():
        suit_cn, suit_en, element = SUIT_NAMES.get(suit_key, (suit_key, suit_key, ""))
        for card in card_list:
            cards.append({
                "name": card["name_cn"],
                "name_en": card["name"],
                "type": f"小阿尔卡那 · {suit_cn}",
                "suit": suit_cn,
                "suit_en": suit_en,
                "suit_key": suit_key,
                "element": element,
                "number": card.get("number"),
                "keywords_upright": card["keywords_upright"],
                "keywords_reversed": card["keywords_reversed"],
                "upright_meaning": card.get("upright_meaning", ""),
                "reversed_meaning": card.get("reversed_meaning", ""),
                "yesno": "yes" if card.get("number", 0) in (1, 6, 9, 10) else
                         "no" if card.get("number", 0) in (5, 7, 8) else "neutral",
            })
    return cards


# ── 抽牌逻辑 ──────────────────────────────────────────────────────────────────

def draw_cards(deck, n):
    drawn = random.sample(deck, min(n, len(deck)))
    return [{"card": c, "reversed": random.random() < 0.5} for c in drawn]


def _cn_number(n):
    return {1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九",10:"十"}.get(n, str(n))


# ── Rich 可视化输出 ──────────────────────────────────────────────────────────

STYLE_GOLD = "bold yellow"
STYLE_CYAN = "bold cyan"
STYLE_DIM = "dim"
STYLE_UPRIGHT = "bold green"
STYLE_REVERSED = "bold red"


def render_card_rich(card_draw, position=None, index=None, show_image=True):
    """渲染单张牌（Rich 模式），图片在 Panel 外直接打印以正确渲染 ANSI 色彩"""
    card = card_draw["card"]
    is_reversed = card_draw["reversed"]
    orientation = (t("reversed"), STYLE_REVERSED) if is_reversed else (t("upright"), STYLE_UPRIGHT)
    keywords = card["keywords_reversed"] if is_reversed else card["keywords_upright"]
    sep = ", " if _LANG == "en" else "、"
    keywords_str = sep.join(keywords) if isinstance(keywords, list) else keywords
    meaning = card["reversed_meaning"] if is_reversed else card["upright_meaning"]

    # 位置标题
    if position and index:
        title = t("position_label").format(_cn_number(index) if _LANG == "zh" else index, position)
    elif position:
        title = position
    else:
        title = t("draw_result")

    # 先打印标题栏
    console.print(f"[{STYLE_GOLD}]{'─' * 40}[/]")
    console.print(f"[{STYLE_GOLD}]  ✦ {title} ✦[/]")
    console.print(f"[{STYLE_GOLD}]{'─' * 40}[/]")

    # 图片直接用 print 输出（保留 ANSI 转义码）
    if show_image:
        url = get_image_url(card)
        img_path = download_image(url)
        art = image_to_unicode(img_path, width=32, reversed_card=is_reversed)
        if art:
            print(art)

    # 文字信息用 Rich
    name_line = Text()
    name_line.append(f"  {card['name']}", style="bold white")
    name_line.append(f"  ({card['name_en']})", style="dim white")
    name_line.append(f"  —  {orientation[0]}", style=orientation[1])
    console.print(name_line)

    kw_line = Text()
    kw_line.append(f"  {t('keywords_label')}", style="dim")
    kw_line.append(keywords_str, style=STYLE_CYAN)
    console.print(kw_line)

    if meaning:
        m_line = Text()
        m_line.append(f"  {t('meaning_label')}", style="dim")
        m_line.append(meaning, style="white")
        console.print(m_line)

    console.print()


def render_card_plain(card_draw, position=None, index=None):
    """纯文本渲染（无 Rich 时回退）"""
    card = card_draw["card"]
    is_reversed = card_draw["reversed"]
    orientation = t("reversed") if is_reversed else t("upright")
    keywords = card["keywords_reversed"] if is_reversed else card["keywords_upright"]
    sep = ", " if _LANG == "en" else "、"
    keywords_str = sep.join(keywords) if isinstance(keywords, list) else keywords

    lines = []
    if position is not None:
        if index:
            label = t("position_label").format(_cn_number(index) if _LANG == "zh" else index, position)
        else:
            label = position
        lines.append(f"【{label}】")
    lines.append(f"  {card['name']} ({card['name_en']}) — {orientation}")
    lines.append(f"  {t('keywords_label')}{keywords_str}")
    meaning = card["reversed_meaning"] if is_reversed else card["upright_meaning"]
    if meaning:
        lines.append(f"  {t('meaning_label')}{meaning}")
    return "\n".join(lines)


# ── 命令处理 ──────────────────────────────────────────────────────────────────

def cmd_draw(args):
    deck = load_cards()
    n = max(1, min(args.n, 78))
    drawn = draw_cards(deck, n)
    title = t("random_draw_n").format(n) if n > 1 else t("random_draw_1")
    if n > 1:
        positions = [t("card_nth").format(_cn_number(i) if _LANG == "zh" else i) for i in range(1, n+1)]
    else:
        positions = [t("guidance")]

    # 文本输出
    _plain_header(title, args.question)
    for i, cd in enumerate(drawn):
        print(render_card_plain(cd, positions[i], i+1 if n > 1 else None))
        print()
    _plain_footer()

    # 生成可视化图片
    img_path = render_spread_image(drawn, positions, title, args.question)
    if img_path:
        print(f"[{t('vis_image')}] {img_path}")
        if getattr(args, 'show', False):
            show_image_window(img_path, title)


def cmd_spread(args):
    spread_type = args.type
    if spread_type not in SPREADS:
        print(f"错误：未知牌阵「{spread_type}」。可用：{', '.join(SPREADS.keys())}")
        sys.exit(1)

    spread_i18n = get_spread_i18n(spread_type)
    deck = load_cards()
    positions = spread_i18n["positions"]
    drawn = draw_cards(deck, len(positions))

    sep = " / " if _LANG == "en" else "／"
    spread_label = f"{spread_i18n['name']}（{sep.join(positions)}）"

    # 文本输出
    _plain_header(f"{t('spread_title')} — {spread_label}", args.question)
    for i, (pos, cd) in enumerate(zip(positions, drawn), 1):
        print(render_card_plain(cd, pos, i))
        print()
    if spread_type == "yesno":
        print(f"  {t('tendency_label')}{_format_yesno(drawn[0])}")
        print()
    _plain_footer()

    # 生成可视化图片
    img_path = render_spread_image(drawn, positions, f"{t('spread_title')} — {spread_i18n['name']}",
                                   args.question, spread_type=spread_type)
    if img_path:
        print(f"[{t('vis_image')}] {img_path}")
        if getattr(args, 'show', False):
            show_image_window(img_path, f"{t('spread_title')} — {spread_i18n['name']}")


def cmd_spreads(_args):
    if HAS_RICH:
        table = Table(title="✦ 可用牌阵一览 ✦", box=box.DOUBLE_EDGE,
                      border_style="yellow", title_style=STYLE_GOLD)
        table.add_column("名称", style="cyan", width=12)
        table.add_column("中文名", style="bold white", width=10)
        table.add_column("张数", style="green", justify="center", width=6)
        table.add_column("说明", style="white", width=35)
        table.add_column("位置", style="dim", width=40)
        for key, sp in SPREADS.items():
            n = len(sp["positions"])
            table.add_row(key, sp["name"], str(n), sp["description"],
                         "、".join(sp["positions"]))
        console.print()
        console.print(table)
        console.print()
        console.print("[dim]用法：python tarot.py spread <牌阵名> -q \"你的问题\"[/]")
    else:
        print("\n可用牌阵：")
        for key, sp in SPREADS.items():
            print(f"  {key:<12} {sp['name']}（{len(sp['positions'])}牌）— {sp['description']}")
        print()


def cmd_card(args):
    deck = load_cards()
    query = args.name.lower().strip()
    matches = [c for c in deck if query in c["name"].lower() or query in c["name_en"].lower()]

    if not matches:
        print(f"错误：未找到与「{args.name}」匹配的牌")
        sys.exit(1)

    if HAS_RICH:
        console.print()
        for card in matches:
            url = get_image_url(card)
            img_path = download_image(url)
            art = image_to_unicode(img_path, width=26)

            lines = []
            if art:
                lines.append(art)
                lines.append("")
            lines.append(Text(f"分类：{card['type']}", style="dim"))
            if card.get("element"):
                lines.append(Text(f"元素：{card['element']}", style="dim"))

            up = "、".join(card['keywords_upright']) if isinstance(card['keywords_upright'], list) else card['keywords_upright']
            rev = "、".join(card['keywords_reversed']) if isinstance(card['keywords_reversed'], list) else card['keywords_reversed']
            up_text = Text()
            up_text.append("正位：", style="green")
            up_text.append(up)
            lines.append(up_text)
            rev_text = Text()
            rev_text.append("逆位：", style="red")
            rev_text.append(rev)
            lines.append(rev_text)

            if card.get("upright_meaning"):
                lines.append(Text())
                m = Text()
                m.append("正位牌义：", style="bold green")
                m.append(card["upright_meaning"])
                lines.append(m)
            if card.get("reversed_meaning"):
                m = Text()
                m.append("逆位牌义：", style="bold red")
                m.append(card["reversed_meaning"])
                lines.append(m)

            from rich.console import Group as RichGroup
            console.print(Panel(
                RichGroup(*lines),
                title=f"[bold yellow]{card['name']} ({card['name_en']})[/]",
                border_style="yellow",
                box=box.DOUBLE,
            ))
            console.print()
    else:
        for card in matches:
            print(f"\n  {card['name']} ({card['name_en']})")
            print(f"  分类：{card['type']}")
            up = "、".join(card['keywords_upright']) if isinstance(card['keywords_upright'], list) else card['keywords_upright']
            rev = "、".join(card['keywords_reversed']) if isinstance(card['keywords_reversed'], list) else card['keywords_reversed']
            print(f"  正位：{up}")
            print(f"  逆位：{rev}")
            print()


def cmd_deck(_args):
    deck = load_cards()
    if HAS_RICH:
        table = Table(title=f"✦ 塔罗全牌一览（共 {len(deck)} 张）✦",
                      box=box.SIMPLE_HEAVY, border_style="yellow", title_style=STYLE_GOLD)
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("中文名", style="bold white", width=12)
        table.add_column("英文名", style="dim", width=25)
        table.add_column("分类", style="cyan", width=18)

        current_type = None
        for card in deck:
            if card["type"] != current_type:
                current_type = card["type"]
                table.add_section()
            num = card.get("number", "")
            table.add_row(str(num), card["name"], card["name_en"], card["type"])
        console.print()
        console.print(table)
        console.print()
    else:
        print(f"\n塔罗全牌（共 {len(deck)} 张）：")
        for card in deck:
            print(f"  {card.get('number',''):>2}  {card['name']} ({card['name_en']})  [{card['type']}]")
        print()


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _format_yesno(card_draw):
    card = card_draw["card"]
    tendency = card["yesno"]
    if card_draw["reversed"]:
        tendency = {"yes": "no", "no": "yes"}.get(tendency, tendency)
    return {"yes": t("yes_tendency"), "no": t("no_tendency"), "neutral": t("neutral_tendency")}.get(tendency, t("neutral_tendency"))


def _plain_header(title, question=None):
    LINE = "═══════════════════════════════════"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{LINE}")
    print(f"  🔮 {title}")
    print(f"  📅 {now}")
    if question:
        print(f"  ❓ {t('question_label')}{question}")
    print(LINE)
    print()


def _plain_footer():
    LINE = "═══════════════════════════════════"
    print(LINE)
    print(f"  {t('ask_claude')}")
    print(f"{LINE}\n")


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="塔罗牌占卜 CLI 工具 / Tarot Reading CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 / Examples:
  python tarot.py draw              随机抽 1 张牌
  python tarot.py draw 3            随机抽 3 张牌
  python tarot.py spread three      三牌阵（过去/现在/未来）
  python tarot.py spread love -q "我和他的关系？"
  python tarot.py spread cross --lang en -q "career advice"
  python tarot.py spreads           列出所有牌阵
  python tarot.py card 愚者         查询「愚者」
  python tarot.py deck              列出全部 78 张牌
""",
    )
    parser.add_argument("--lang", type=str, default="zh", choices=["zh", "en"],
                        help="输出语言 / output language (zh/en, default: zh)")
    sub = parser.add_subparsers(dest="command")

    p_draw = sub.add_parser("draw", help="随机抽牌")
    p_draw.add_argument("n", nargs="?", type=int, default=1)
    p_draw.add_argument("-q", "--question", type=str, default=None)
    p_draw.add_argument("-s", "--show", action="store_true", help="弹窗显示可视化图片")

    p_spread = sub.add_parser("spread", help="使用指定牌阵")
    p_spread.add_argument("type", type=str)
    p_spread.add_argument("-q", "--question", type=str, default=None)
    p_spread.add_argument("-s", "--show", action="store_true", help="弹窗显示可视化图片")

    sub.add_parser("spreads", help="列出所有可用牌阵")

    p_card = sub.add_parser("card", help="查询指定牌")
    p_card.add_argument("name", type=str)

    sub.add_parser("deck", help="列出全部 78 张牌")

    args = parser.parse_args()

    global _LANG
    _LANG = args.lang
    if not args.command:
        parser.print_help()
        sys.exit(0)

    {"draw": cmd_draw, "spread": cmd_spread, "spreads": cmd_spreads,
     "card": cmd_card, "deck": cmd_deck}[args.command](args)


if __name__ == "__main__":
    main()
