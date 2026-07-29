"""
Export painted hex grid to a PNG image.
- No borders
- Colored hexes at 50% opacity, transparent elsewhere (100% transparent = mask cut)
- Masked by map-borders-2x-prefill.png (transparent areas in mask -> transparent in output)
- Pure software rendering with Pillow (no GPU needed)

Usage:
    python export.py [input.json] [output.png]
    python export.py                          # uses default paths
"""

import os
import sys
import math
import json
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from hex_model import HexGrid, hex_pixel_center, compute_grid_size, SIDE, HEX_W_EXACT, ROW_STEP

# --- Paths ---
DEFAULT_INPUT  = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "hex_grid_data.json")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "hex_export.png")
MASK_PATH      = os.path.join(os.path.dirname(__file__), "..", "..", "maps", "map-borders-2x-prefill.png")

MAP_W, MAP_H = 9000, 8508

PALETTE = [
    (0,   0,   0),    # 0: empty
    (255, 0,   0),    # 1
    (0,   255, 0),    # 2
    (0,   128, 255),  # 3
    (255, 255, 0),    # 4
    (255, 128, 0),    # 5
    (128, 0,   255),  # 6
    (0,   255, 255),  # 7
    (255, 0,   255),  # 8
    (128, 128, 128),  # 9
    (192, 64,  0),    # 10
    (0,   192, 128),  # 11
    (64,  64,  255),  # 12
    (255, 192, 128),  # 13
    (128, 255, 128),  # 14
    (192, 128, 255),  # 15
]

COLORED_ALPHA = 128   # 50% opacity  (0-255)
EMPTY_ALPHA   = 0     # fully transparent

# Slightly inflate hexes to cover 1px seam left by removed borders
FILL_SIDE = SIDE + 0.5


def make_hex_polygon(cx: float, cy: float, side: float) -> list[tuple[float, float]]:
    """Return 6 vertices for a tip-up (pointy-top) hex centered at (cx, cy)."""
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        pts.append((cx + side * math.cos(angle), cy + side * math.sin(angle)))
    return pts


def export(input_path: str, output_path: str):
    # Load grid data
    print(f"Loading grid: {input_path}")
    grid = HexGrid.load(input_path)
    print(f"Grid size: {grid.cols} x {grid.rows}")

    # Create RGBA canvas, fully transparent
    canvas = Image.new("RGBA", (MAP_W, MAP_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Draw filled hexes (no borders)
    painted = 0
    for r in range(grid.rows):
        for c in range(grid.cols):
            i1 = int(grid.idx1[r, c])
            i2 = int(grid.idx2[r, c])

            if i1 == 0 and i2 == 0:
                continue  # empty cell — leave transparent

            cx, cy = hex_pixel_center(c, r)
            poly = make_hex_polygon(cx, cy, FILL_SIDE)

            if i2 == 0:
                # Single color: fill whole hex
                rgb = PALETTE[i1] if i1 < len(PALETTE) else (0, 0, 0)
                draw.polygon(poly, fill=(*rgb, COLORED_ALPHA))
            else:
                # Two colors: split diagonally (mirrors shader logic: x+y < 5 -> color1)
                # Approximate split by drawing two halves; use hex bounding box clip
                # We draw color2 first (whole hex), then overdraw color1 half as a clipped polygon
                rgb1 = PALETTE[i1] if i1 < len(PALETTE) else (0, 0, 0)
                rgb2 = PALETTE[i2] if i2 < len(PALETTE) else (0, 0, 0)

                # Collect which vertices are on color1 side (local x+y < 5)
                local_pts = [(px - cx, py - cy) for px, py in poly]
                c1_side = [lp[0] + lp[1] < 5.0 for lp in local_pts]

                # Build sub-polygon for color1 half (vertices on its side + interpolated crossings)
                c1_poly = _split_polygon(poly, local_pts, c1_side, cx, cy)
                c2_poly = _split_polygon(poly, local_pts, [not s for s in c1_side], cx, cy)

                if c2_poly:
                    draw.polygon(c2_poly, fill=(*rgb2, COLORED_ALPHA))
                if c1_poly:
                    draw.polygon(c1_poly, fill=(*rgb1, COLORED_ALPHA))

            painted += 1

    print(f"Drew {painted} colored cells")

    # Apply mask: transparent pixels in mask -> transparent in output
    print(f"Loading mask: {MASK_PATH}")
    mask_img = Image.open(MASK_PATH).convert("RGBA")

    # Resize mask to match canvas if needed
    if mask_img.size != (MAP_W, MAP_H):
        print(f"  Resizing mask from {mask_img.size} to {(MAP_W, MAP_H)}")
        mask_img = mask_img.resize((MAP_W, MAP_H), Image.LANCZOS)

    mask_alpha = np.array(mask_img)[:, :, 3]  # shape (H, W), uint8

    canvas_arr = np.array(canvas)  # (H, W, 4)

    # Mask convention: transparent pixels in mask = land (valid area).
    # Opaque pixels in mask = outside/ocean -> cut those from output.
    outside = mask_alpha >= 128
    canvas_arr[outside, 3] = 0

    result = Image.fromarray(canvas_arr, "RGBA")
    result.save(output_path)
    print(f"Saved: {output_path}")


def _split_polygon(
    world_pts: list[tuple[float, float]],
    local_pts: list[tuple[float, float]],
    on_side: list[bool],
    cx: float,
    cy: float,
) -> list[tuple[float, float]]:
    """
    Sutherland-Hodgman style: collect vertices on `on_side` and insert
    intersection points where the edge crosses the split line (x+y == 5).
    """
    result = []
    n = len(world_pts)
    for i in range(n):
        j = (i + 1) % n
        lp_i = local_pts[i]
        lp_j = local_pts[j]
        val_i = lp_i[0] + lp_i[1]
        val_j = lp_j[0] + lp_j[1]
        side_i = on_side[i]
        side_j = on_side[j]

        if side_i:
            result.append(world_pts[i])

        # Edge crosses the split line
        if side_i != side_j:
            # Interpolate crossing at val == 5.0
            denom = (val_j - val_i)
            if abs(denom) > 1e-9:
                t = (5.0 - val_i) / denom
                wx = world_pts[i][0] + t * (world_pts[j][0] - world_pts[i][0])
                wy = world_pts[i][1] + t * (world_pts[j][1] - world_pts[i][1])
                result.append((wx, wy))

    return result if len(result) >= 3 else []


if __name__ == "__main__":
    input_path  = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    export(input_path, output_path)
