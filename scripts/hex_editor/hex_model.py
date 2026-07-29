"""Hex grid data model using integer offset coordinates (odd-r, tip-up/pointy-top)."""

import json
import numpy as np

SIDE = 15  # edge length in px

# Precomputed integer-friendly constants for tip-up hex:
# hex_w = sqrt(3) * side  (horizontal distance between centers in same row)
# row_step = 1.5 * side   (vertical distance between row centers)
# For pixel mapping we store multipliers and compute final floats only at render time.

HEX_W_EXACT = np.sqrt(3) * SIDE  # ~25.98
ROW_STEP = 1.5 * SIDE  # 22.5 (exact)


def hex_pixel_center(col: int, row: int) -> tuple[float, float]:
    """Convert offset coords (odd-r) to pixel center. Odd rows shifted right."""
    x = col * HEX_W_EXACT + (HEX_W_EXACT * 0.5 if (row & 1) else 0.0)
    y = row * ROW_STEP
    return (x, y)


def pixel_to_hex(px: float, py: float) -> tuple[int, int]:
    """Convert pixel position to nearest hex offset coord (odd-r, tip-up)."""
    # Approximate row
    row_approx = py / ROW_STEP
    row = int(round(row_approx))

    # Given row, compute x offset
    offset = (HEX_W_EXACT * 0.5) if (row & 1) else 0.0
    col = int(round((px - offset) / HEX_W_EXACT))

    # Check neighbors for closest center (handles edge cases)
    best = (col, row)
    best_dist = (px - hex_pixel_center(col, row)[0]) ** 2 + (py - hex_pixel_center(col, row)[1]) ** 2
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            c2, r2 = col + dc, row + dr
            cx, cy = hex_pixel_center(c2, r2)
            d = (px - cx) ** 2 + (py - cy) ** 2
            if d < best_dist:
                best_dist = d
                best = (c2, r2)
    return best


class HexGrid:
    """Stores per-cell data for a fixed-size hex grid. Each cell has two color indices."""

    def __init__(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        # Two palette index attributes per cell (0 = empty/transparent)
        self.idx1 = np.zeros((rows, cols), dtype=np.uint8)
        self.idx2 = np.zeros((rows, cols), dtype=np.uint8)

    def set_idx1(self, col: int, row: int, idx: int):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.idx1[row, col] = idx

    def set_idx2(self, col: int, row: int, idx: int):
        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.idx2[row, col] = idx

    def get_idx1(self, col: int, row: int) -> int:
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return int(self.idx1[row, col])
        return 0

    def get_idx2(self, col: int, row: int) -> int:
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return int(self.idx2[row, col])
        return 0

    def save(self, path: str):
        data = {
            "cols": self.cols,
            "rows": self.rows,
            "idx1": self.idx1.tolist(),
            "idx2": self.idx2.tolist(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> "HexGrid":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        grid = cls(data["cols"], data["rows"])
        grid.idx1 = np.array(data["idx1"], dtype=np.uint8)
        grid.idx2 = np.array(data["idx2"], dtype=np.uint8)
        return grid


def compute_grid_size(map_w: int, map_h: int) -> tuple[int, int]:
    """Compute how many hex columns and rows fit in a map of given pixel size."""
    cols = int(map_w / HEX_W_EXACT) + 1
    rows = int(map_h / ROW_STEP) + 1
    return cols, rows
