"""Extract Chinese characters from a file and render them into 1-bit BMP files."""

import argparse
import csv
import math
import struct
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CHAR_PX = 16
CHARS_PER_ROW = 32
IMG_WIDTH = CHAR_PX * CHARS_PER_ROW  # 512PX
MAX_FILE_SIZE = 63 * 1024  # 63KB

# BMP 1-bit header size: 14 (file header) + 40 (DIB) + 8 (color table) = 62
BMP_HEADER_SIZE = 62
BYTES_PER_SCANLINE = IMG_WIDTH // 8  # 32 bytes, already 4-byte aligned
MAX_SCANLINES = (MAX_FILE_SIZE - BMP_HEADER_SIZE) // BYTES_PER_SCANLINE
MAX_CHAR_ROWS = MAX_SCANLINES // CHAR_PX
MAX_CHARS_PER_FILE = MAX_CHAR_ROWS * CHARS_PER_ROW


def is_chinese(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0x20000 <= cp <= 0x2A6DF
        or 0xF900 <= cp <= 0xFAFF
    )


def extract_chinese(text: str) -> list[tuple[str, int]]:
    freq = Counter(ch for ch in text if is_chinese(ch))
    return freq.most_common()


def render_bmp(chars: list[str], font: ImageFont.FreeTypeFont, output: Path):
    rows = math.ceil(len(chars) / CHARS_PER_ROW)
    height = rows * CHAR_PX
    img = Image.new("1", (IMG_WIDTH, height), color=1)  # white background
    draw = ImageDraw.Draw(img)

    ascent, descent = font.getmetrics()
    baseline_y = (CHAR_PX - (ascent + descent)) // 2 + ascent

    for i, ch in enumerate(chars):
        col = i % CHARS_PER_ROW
        row = i // CHARS_PER_ROW
        x = col * CHAR_PX + CHAR_PX // 2
        y = row * CHAR_PX + baseline_y
        draw.text((x, y), ch, fill=0, font=font, anchor="ms")

    img.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input text file")
    parser.add_argument("-f", "--font", default=str(Path(__file__).parent / "unifont.otf"))
    parser.add_argument("-o", "--output-dir", default="output")
    parser.add_argument("-p", "--prefix", default="chars")
    args = parser.parse_args()

    text = Path(args.input).read_text(encoding="utf-8")
    freq = extract_chinese(text)
    if not freq:
        print("No Chinese characters found.")
        sys.exit(0)

    chars = [ch for ch, _ in freq]
    print(f"Found {len(chars)} unique Chinese characters.")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    font = ImageFont.truetype(args.font, CHAR_PX)

    # Split into chunks and render
    chunks = [chars[i:i + MAX_CHARS_PER_FILE] for i in range(0, len(chars), MAX_CHARS_PER_FILE)]
    mapping_rows = []

    for file_idx, chunk in enumerate(chunks):
        filename = f"{args.prefix}_{file_idx:03d}.bmp"
        render_bmp(chunk, font, out_dir / filename)
        for local_idx, ch in enumerate(chunk):
            mapping_rows.append((ch, freq[chars.index(ch)][1] if False else 0, filename, local_idx))
        print(f"  {filename}: {len(chunk)} chars")

    # Build CSV with frequency info
    char_freq = dict(freq)
    csv_path = out_dir / f"{args.prefix}_map.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["char", "codepoint", "freq", "file", "index"])
        for file_idx, chunk in enumerate(chunks):
            filename = f"{args.prefix}_{file_idx:03d}.bmp"
            for local_idx, ch in enumerate(chunk):
                writer.writerow([ch, f"U+{ord(ch):04X}", char_freq[ch], filename, local_idx])

    print(f"Mapping saved to {csv_path}")


if __name__ == "__main__":
    main()
