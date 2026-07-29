"""Generate a blank hex grid data file, masked by transparent regions in the map image."""

import os
import sys
import json
import math
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from hex_model import compute_grid_size, hex_pixel_center, SIDE

MAP_W, MAP_H = 9000, 8508
BG_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "map-borders-2x-prefill.png")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "blank.json")

# Classic pride flag bands (top to bottom): red, orange, yellow, green, blue, purple
# Mapped to palette indices in main.py
BANDS = [9, 9, 9, 9, 9, 9]  # red, orange, yellow, green, blue, purple
BAND_HEIGHT = 6  # rows per band, then cycle

cols, rows = compute_grid_size(MAP_W, MAP_H)
print(f"Grid size: {cols} x {rows}")

# Load image alpha channel as mask
print(f"Loading mask image: {BG_IMAGE_PATH}")
img = Image.open(BG_IMAGE_PATH).convert("RGBA")
alpha = np.array(img)[:, :, 3]  # shape: (img_h, img_w)
img_h, img_w = alpha.shape
print(f"Image size: {img_w} x {img_h}")

# Precompute hex bounding box radius for sampling
# For a tip-up hex with given SIDE, the bounding box is roughly:
#   width = sqrt(3) * SIDE, height = 2 * SIDE
# We'll sample a grid of points within the hex's bounding box and check alpha
SAMPLE_RADIUS = int(SIDE * 0.8)

idx1 = np.zeros((rows, cols), dtype=np.uint8)
idx2 = np.zeros((rows, cols), dtype=np.uint8)

filled = 0
for r in range(rows):
    band_idx = (r // BAND_HEIGHT) % len(BANDS)
    color = BANDS[band_idx]
    for c in range(cols):
        cx, cy = hex_pixel_center(c, r)
        # Sample a small region around the hex center
        x_min = max(0, int(cx) - SAMPLE_RADIUS)
        x_max = min(img_w, int(cx) + SAMPLE_RADIUS + 1)
        y_min = max(0, int(cy) - SAMPLE_RADIUS)
        y_max = min(img_h, int(cy) + SAMPLE_RADIUS + 1)

        if x_min >= x_max or y_min >= y_max:
            continue

        # Check if any pixel in the region is transparent (alpha < 128)
        region = alpha[y_min:y_max, x_min:x_max]
        if np.any(region < 128):
            idx1[r, c] = color
            filled += 1

print(f"Filled {filled} / {rows * cols} cells ({100 * filled / (rows * cols):.1f}%)")

data = {
    "cols": int(cols),
    "rows": int(rows),
    "idx1": idx1.tolist(),
    "idx2": idx2.tolist(),
}

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f)

print(f"Blank grids saved to {OUTPUT_PATH}")
print(f"Load it in the editor with: python main.py \"{OUTPUT_PATH}\"")
