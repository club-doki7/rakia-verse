"""Generate a 1-bit BMP for ASCII 32~127 (8x16 per character)."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHAR_W = 8
CHAR_H = 16
CHARS_PER_ROW = 32
IMG_WIDTH = CHAR_W * CHARS_PER_ROW  # 256px

FONT_PATH = Path(__file__).parent / "unifont.otf"
OUTPUT_PATH = Path(__file__).parent / "output" / "ascii.bmp"


def main():
    chars = [chr(c) for c in range(33, 127)]  # 94 characters
    rows = math.ceil(len(chars) / CHARS_PER_ROW)
    height = rows * CHAR_H

    img = Image.new("1", (IMG_WIDTH, height), color=1)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT_PATH), CHAR_H)

    ascent, descent = font.getmetrics()
    # Center the font's ascent+descent block vertically, then anchor to baseline
    baseline_y = (CHAR_H - (ascent + descent)) // 2 + ascent

    for i, ch in enumerate(chars):
        col = i % CHARS_PER_ROW
        row = i // CHARS_PER_ROW
        x = col * CHAR_W + CHAR_W // 2
        y = row * CHAR_H + baseline_y
        draw.text((x, y), ch, fill=0, font=font, anchor="ms")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH)
    print(f"Generated {OUTPUT_PATH} ({IMG_WIDTH}x{height}, {len(chars)} chars)")


if __name__ == "__main__":
    main()
