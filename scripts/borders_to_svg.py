"""
borders_to_svg.py
把 1px 边界 PNG 转成 SVG（用 OpenCV findContours）。
输入：maps/map-borders-1px.png
输出：maps/map-borders.svg

用法：
    python _scripts/borders_to_svg.py
    python _scripts/borders_to_svg.py maps/map-borders-1px.png maps/map-borders.svg
"""

import sys
import numpy as np
import cv2


def png_to_svg(src_path: str, dst_path: str) -> None:
    img = cv2.imread(src_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {src_path}")

    # 获取前景掩码
    if img.ndim == 3 and img.shape[2] == 4:
        mask = img[:, :, 3]
    else:
        gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

    h, w = mask.shape

    # 膨胀一下让 findContours 能抓到连通轮廓
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(mask, kernel, iterations=1)

    # CHAIN_APPROX_NONE 保留所有轮廓点，最大精度
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        '<g fill="none" stroke="black" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">',
    ]

    min_points = 5
    count = 0
    for cnt in contours:
        pts = cnt.reshape(-1, 2)
        if len(pts) < min_points:
            continue
        d = f"M{pts[0][0]},{pts[0][1]}"
        for x, y in pts[1:]:
            d += f" L{x},{y}"
        d += " Z"
        parts.append(f'  <path vector-effect="non-scaling-stroke" d="{d}"/>')
        count += 1

    parts.append("</g>")
    parts.append("</svg>")

    svg_content = "\n".join(parts)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"已保存：{dst_path}")
    print(f"路径数：{count}，文件大小：{len(svg_content)/1024:.1f} KB")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "maps/map-borders-1px.png"
    dst = sys.argv[2] if len(sys.argv) > 2 else "maps/map-borders.svg"
    png_to_svg(src, dst)
