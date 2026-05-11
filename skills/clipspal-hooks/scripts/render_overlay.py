#!/usr/bin/env python3
"""render_overlay.py — render a hook line to a transparent 1080x1920 PNG with
TikTok Sans Bold + inline Apple color emoji.

This is the Python/Pillow replica of libs/captions/render-overlay.js
(Satori + resvg + apple-emoji from jsdelivr) used by the ClipsPal Lambda
caption pipeline. We render to PNG and let ffmpeg overlay it, so we get
real color emoji that drawtext can never produce.

Usage:
  render_overlay.py "<text>" <out_path> [--appearance outlined|bold_yellow]
                                        [--font-size 60]
                                        [--max-line-chars 24]
                                        [--canvas-w 1080] [--canvas-h 1920]
                                        [--position top|middle|bottom]
"""

from __future__ import annotations
import argparse
import io
import os
import re
import sys
import urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SKILL_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = SKILL_DIR / "fonts"
EMOJI_CACHE_DIR = Path(os.environ.get(
    "CLIPSPAL_EMOJI_CACHE",
    str(Path.home() / ".cache" / "clipspal" / "emoji"),
))
EMOJI_CDN = "https://cdn.jsdelivr.net/npm/emoji-datasource-apple@15.1.2/img/apple/64"

# Same Unicode ranges the prod Multilingual loader keys on (multilingual-fonts.js)
FALLBACK_FONTS = [
    ("NotoNaskhArabic-Bold.ttf", re.compile(
        r"[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]"
    )),
    ("NotoSansHebrew-Bold.ttf", re.compile(r"[֐-׿יִ-ﭏ]")),
    ("NotoSansDevanagari-Bold.ttf", re.compile(r"[ऀ-ॿ]")),
    ("NotoSansThai-Bold.ttf", re.compile(r"[฀-๿]")),
    # Cyrillic / Greek / extended Latin diacritics
    ("NotoSans-Bold.ttf", re.compile(r"[Ͱ-ӿĀ-ɏḀ-ỿ]")),
]

# Conservative Extended_Pictographic-ish ranges. Captures every emoji we ship
# in the prod free tool. ZWJ (U+200D) and VS16 (U+FE0F) are joined into the
# preceding grapheme cluster by the cluster scanner below.
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F680-\U0001F6FF"  # transport
    "\U0001F700-\U0001F77F"  # alchemical
    "\U0001F780-\U0001F7FF"  # geometric ext
    "\U0001F800-\U0001F8FF"  # arrows-c
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FAFF"  # symbols & pictographs ext-a/b
    "☀-⛿"          # misc symbols
    "✀-➿"          # dingbats
    "]"
)


def emoji_codepoint(cluster: str) -> str:
    """Convert an emoji grapheme cluster to the apple-emoji filename
    convention: hex codepoints joined by '-', with FE0F (VS16) stripped."""
    return "-".join(
        f"{ord(c):x}" for c in cluster if ord(c) != 0xFE0F
    )


def load_emoji_image(cluster: str, size: int) -> Image.Image | None:
    """Fetch the Apple emoji PNG for this cluster (cached on disk). Returns
    a resized PIL Image or None if not available."""
    cp = emoji_codepoint(cluster)
    EMOJI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = EMOJI_CACHE_DIR / f"{cp}.png"
    if not cache_path.exists():
        url = f"{EMOJI_CDN}/{cp}.png"
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = resp.read()
            cache_path.write_bytes(data)
        except Exception as e:
            print(f"[render-overlay] emoji fetch failed for {cp}: {e}", file=sys.stderr)
            return None
    try:
        img = Image.open(cache_path).convert("RGBA")
        return img.resize((size, size), Image.LANCZOS)
    except Exception:
        return None


def segment_clusters(text: str) -> list[str]:
    """Walk the string and group ZWJ-joined / VS16-suffixed emoji into single
    cluster strings. Naive but covers everything we render."""
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        cluster = c
        j = i + 1
        # Greedily absorb VS16, ZWJ + next char, and skin-tone modifiers
        while j < n:
            nxt = text[j]
            if nxt == "️":
                cluster += nxt
                j += 1
                continue
            if nxt == "‍" and j + 1 < n:
                cluster += nxt + text[j + 1]
                j += 2
                continue
            # Fitzpatrick skin-tone modifiers
            if 0x1F3FB <= ord(nxt) <= 0x1F3FF:
                cluster += nxt
                j += 1
                continue
            break
        out.append(cluster)
        i = j
    return out


def split_line_segments(line: str) -> list[tuple[str, str]]:
    """Return a list of (kind, value) tuples where kind in {'text','emoji'}.
    Each emoji is its full grapheme cluster."""
    out: list[tuple[str, str]] = []
    buf = ""
    for cluster in segment_clusters(line):
        # cluster of length 1 with non-emoji char → text; emoji clusters
        # (including ZWJ/VS16/skin-tone joined ones) → emoji.
        first = cluster[0]
        if EMOJI_RE.fullmatch(first) or len(cluster) > 1 and any(EMOJI_RE.fullmatch(c) for c in cluster):
            if buf:
                out.append(("text", buf))
                buf = ""
            out.append(("emoji", cluster))
        else:
            buf += cluster
    if buf:
        out.append(("text", buf))
    return out


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = [w for w in re.split(r"\s+", text) if w]
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if len(trial) <= max_chars or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def pick_font_for_text(text: str, size: int) -> ImageFont.FreeTypeFont:
    """Choose primary font for the rendering pass. If any character in `text`
    matches a fallback's range, use that fallback. Otherwise TikTok Sans."""
    for fname, regex in FALLBACK_FONTS:
        if regex.search(text):
            path = FONTS_DIR / fname
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
    return ImageFont.truetype(str(FONTS_DIR / "TikTokSans-Bold.ttf"), size=size)


def measure_segment(seg_kind: str, seg_val: str, font: ImageFont.FreeTypeFont, em_size: int) -> int:
    if seg_kind == "emoji":
        return em_size
    dummy = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), seg_val, font=font)
    return bbox[2] - bbox[0]


def render(
    text: str,
    out_path: Path,
    appearance: str = "outlined",
    font_size: int = 60,
    max_line_chars: int = 24,
    canvas_w: int = 1080,
    canvas_h: int = 1920,
    position: str = "middle",
) -> None:
    is_yellow = appearance == "bold_yellow"
    fill_color = (255, 230, 0, 255) if is_yellow else (255, 255, 255, 255)
    stroke_w = 6 if is_yellow else 4
    line_height = int(font_size * 1.2)

    if is_yellow:
        text = text.upper()

    lines = wrap_text(text, max_line_chars)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    font = pick_font_for_text(text, font_size)
    em_size = font_size

    # Total block height for vertical positioning
    total_h = line_height * len(lines)
    if position == "top":
        y0 = int(canvas_h * 0.18) - total_h // 2
    elif position == "bottom":
        y0 = canvas_h - int(canvas_h * 0.18) - total_h
    else:  # middle
        y0 = (canvas_h - total_h) // 2

    for li, line in enumerate(lines):
        segments = split_line_segments(line)
        widths = [measure_segment(k, v, font, em_size) for (k, v) in segments]
        line_w = sum(widths)
        x = (canvas_w - line_w) // 2
        y = y0 + li * line_height

        for (kind, val), w in zip(segments, widths):
            if kind == "emoji":
                img = load_emoji_image(val, em_size)
                if img is not None:
                    # Vertically center the emoji glyph on the text baseline
                    canvas.alpha_composite(img, (x, y + (line_height - em_size) // 2))
                    x += w
                else:
                    # Fall back to text rendering so the user doesn't see a
                    # silent gap when the apple-emoji CDN has no asset for
                    # this codepoint (e.g. U+2605 BLACK STAR).
                    draw.text(
                        (x, y),
                        val,
                        font=font,
                        fill=fill_color,
                        stroke_width=stroke_w,
                        stroke_fill=(0, 0, 0, 255),
                    )
                    bbox = draw.textbbox((0, 0), val, font=font)
                    x += bbox[2] - bbox[0]
            else:
                draw.text(
                    (x, y),
                    val,
                    font=font,
                    fill=fill_color,
                    stroke_width=stroke_w,
                    stroke_fill=(0, 0, 0, 255),
                )
                x += w

    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, "PNG")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("text")
    p.add_argument("out")
    p.add_argument("--appearance", default="outlined", choices=["outlined", "bold_yellow"])
    p.add_argument("--font-size", type=int, default=60)
    p.add_argument("--max-line-chars", type=int, default=24)
    p.add_argument("--canvas-w", type=int, default=1080)
    p.add_argument("--canvas-h", type=int, default=1920)
    p.add_argument("--position", default="middle", choices=["top", "middle", "bottom"])
    args = p.parse_args()
    render(
        args.text,
        Path(args.out),
        appearance=args.appearance,
        font_size=args.font_size,
        max_line_chars=args.max_line_chars,
        canvas_w=args.canvas_w,
        canvas_h=args.canvas_h,
        position=args.position,
    )
    print(f"DONE:{args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
