import numpy as np
import cv2
import math

width, height = 9000, 8508

# BGRA - transparent background
img = np.zeros((height, width, 4), dtype=np.uint8)

side = 15  # edge length in px
# Tip-up (pointy-top) hexagon
hex_w = math.sqrt(3) * side

# Vertical spacing between row centers = 1.5 * side
row_step = 1.5 * side
# Horizontal spacing between column centers = hex_w
col_step = hex_w


def hex_vertices(cx, cy, s):
    pts = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        x = cx + s * math.cos(angle)
        y = cy + s * math.sin(angle)
        pts.append((int(round(x)), int(round(y))))
    return np.array(pts, dtype=np.int32)


# Draw grid
row = 0
cy = 0
while cy - side <= height:
    offset = (hex_w / 2) if (row % 2 == 1) else 0
    cx = offset
    while cx - side <= width:
        pts = hex_vertices(cx, cy, side)
        cv2.polylines(img, [pts], isClosed=True, color=(0, 0, 0, 255), thickness=1)
        cx += col_step
    cy += row_step
    row += 1

cv2.imwrite(r"..\maps\hex-grid.png", img)
print("Done", img.shape)
