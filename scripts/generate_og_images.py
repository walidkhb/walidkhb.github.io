#!/usr/bin/env python3
"""
Generate branded 1200x630 social-share (Open Graph) images for each article.

One PNG per article is written to assets/img/og/<slug>.png, on-brand with the
site: dark canvas, mint accent, Inter type, category label + headline.

Requires Pillow and an Inter TTF. The Inter variable font is fetched into
build/fonts/Inter.ttf by the setup step; falls back to a system sans if absent.

Re-run whenever you add an article or change a headline.
"""

import glob
import html
import json
import os
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "assets", "img", "og")

W, H = 1200, 630
PAD = 84

# Palette (from assets/css/style.css :root)
BG = (10, 10, 15)            # --color-bg
BG2 = (15, 15, 22)           # --color-bg-alt
ACCENT = (0, 212, 170)       # --color-accent
TEXT = (244, 244, 245)
TEXT_SECONDARY = (161, 161, 170)
TEXT_MUTED = (113, 113, 122)

INTER_URL = "https://github.com/google/fonts/raw/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"


def ensure_inter():
    """Return a path to Inter.ttf, downloading it on first run if needed."""
    target = os.path.join(ROOT, "build", "fonts", "Inter.ttf")
    if os.path.exists(target):
        return target
    try:
        import urllib.request

        os.makedirs(os.path.dirname(target), exist_ok=True)
        urllib.request.urlretrieve(INTER_URL, target)
        return target
    except Exception:
        return None


FONT_CANDIDATES = [
    ensure_inter(),
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if p and os.path.exists(p)), None)
IS_INTER = bool(FONT_PATH) and FONT_PATH.endswith("Inter.ttf")

JSONLD_RE = re.compile(
    r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', re.S
)


def font(size, weight="Regular"):
    if not FONT_PATH:
        return ImageFont.load_default()
    f = ImageFont.truetype(FONT_PATH, size)
    if IS_INTER:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def collect_articles():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "blog", "*.html"))):
        text = open(path, encoding="utf-8").read()
        post = None
        for blob in JSONLD_RE.findall(text):
            try:
                data = json.loads(blob)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get("@type") == "BlogPosting":
                post = data
                break
        if not post:
            continue
        slug = os.path.basename(path)[:-5]
        title = html.unescape(post.get("headline", slug)).strip()
        category = ""
        for item in post.get("breadcrumb", {}).get("itemListElement", []):
            if item.get("position") == 3:
                category = html.unescape(item.get("name", "")).upper()
        out.append((slug, title, category))
    return out


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def tracked_text(draw, xy, text, fnt, fill, tracking):
    """Draw text with manual letter-spacing (Pillow has no native tracking)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def render(slug, title, category):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Vertical wash for depth
    for y in range(H):
        t = y / H
        r = int(BG[0] + (BG2[0] - BG[0]) * t)
        g = int(BG[1] + (BG2[1] - BG[1]) * t)
        b = int(BG[2] + (BG2[2] - BG[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # Accent rail down the left edge
    draw.rectangle([0, 0, 8, H], fill=ACCENT)

    # Decorative stacked bars (echo of the logo / platform motif), top-right, clear of text
    bx, by = W - 234, PAD + 6
    for i in range(3):
        y0 = by + i * 26
        draw.rounded_rectangle([bx + i * 46, y0, bx + 150, y0 + 12], radius=6,
                               fill=ACCENT if i == 0 else (26, 42, 40))

    # Wordmark, top-left
    mark = font(34, "Bold")
    draw.text((PAD, PAD), "W", font=mark, fill=TEXT)
    wlen = draw.textlength("W", font=mark)
    draw.text((PAD + wlen, PAD), ".", font=mark, fill=ACCENT)
    dlen = draw.textlength(".", font=mark)
    draw.text((PAD + wlen + dlen + 6, PAD), "Albadawi", font=font(34, "SemiBold"), fill=TEXT)

    # Category overline
    cat_font = font(23, "Bold")
    cat_y = 196
    if category:
        tracked_text(draw, (PAD, cat_y), category, cat_font, ACCENT, 2.5)
        draw.line([(PAD, cat_y + 42), (PAD + 54, cat_y + 42)], fill=ACCENT, width=3)

    # Headline — adaptive size, vertically centered in a fixed band so 1–4 lines all sit cleanly
    max_w = W - 2 * PAD - 24
    for size, lh in ((62, 78), (58, 72), (52, 64)):
        title_font = font(size, "Bold")
        lines = wrap(draw, title, title_font, max_w)
        if len(lines) <= 3 or size == 52:
            break
    lines = lines[:4]
    band_top, band_bottom = 272, H - 122
    total_h = len(lines) * lh
    ty = band_top + max(0, (band_bottom - band_top - total_h) // 2)
    for ln in lines:
        draw.text((PAD, ty), ln, font=title_font, fill=TEXT)
        ty += lh

    # Footer line
    foot = font(22, "Medium")
    fy = H - PAD + 2
    draw.text((PAD, fy), "wbadawi.info", font=foot, fill=TEXT_SECONDARY)
    wl = draw.textlength("wbadawi.info", font=foot)
    draw.text((PAD + wl + 14, fy), "•", font=foot, fill=ACCENT)
    draw.text((PAD + wl + 32, fy), "Enterprise Integration · KSA", font=foot, fill=TEXT_MUTED)

    os.makedirs(OUT_DIR, exist_ok=True)
    img.save(os.path.join(OUT_DIR, f"{slug}.png"), "PNG")


def main():
    if not FONT_PATH:
        print("  ! No usable font found; images will use a bitmap fallback.")
    elif not IS_INTER:
        print(f"  ! Inter not found, using fallback: {FONT_PATH}")
    arts = collect_articles()
    for slug, title, category in arts:
        render(slug, title, category)
        print(f"  og/{slug}.png   [{category}]")
    print(f"\n  {len(arts)} images → assets/img/og/")


if __name__ == "__main__":
    main()
