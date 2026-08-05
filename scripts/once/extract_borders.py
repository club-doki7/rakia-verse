"""
extract_borders.py
把地图大陆边界提取成 1 像素厚的线条。
输入：maps/map.png（白底蓝色轮廓）
输出：maps/map-borders-1px.png（白底黑色 1px 轮廓）

用法：
    python _scripts/extract_borders.py
    python _scripts/extract_borders.py maps/map.png maps/map-borders-1px.png
"""

import sys
import numpy as np
import cv2

def extract_1px_borders(src_path: str, dst_path: str) -> None:
    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {src_path}")

    # --- 1. 把非白色像素视为"线条"，生成二值掩码 ---
    # 白色背景 ≈ (255, 255, 255)；轮廓是淡蓝色，明显偏离纯白。
    # 用 L2 距离与纯白的差值阈值来容纳抗锯齿边缘。
    white = np.array([255, 255, 255], dtype=np.float32)
    diff = np.linalg.norm(img.astype(np.float32) - white, axis=2)
    _, mask = cv2.threshold(diff.astype(np.uint8), 15, 255, cv2.THRESH_BINARY)

    # --- 2. 用 Zhang-Suen thinning 细化到 1px ---
    # cv2.ximgproc.thinning 要求 8-bit 单通道，前景为 255
    thin = cv2.ximgproc.thinning(mask, thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)

    # --- 3. 合成输出：白底 + 黑色 1px 线 ---
    out = np.full_like(img, 255)
    out[thin == 255] = [0, 0, 0]

    cv2.imwrite(dst_path, out)
    print(f"已保存：{dst_path}")
    nonzero = int(np.count_nonzero(thin))
    print(f"线条像素数：{nonzero:,}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "maps/map.png"
    dst = sys.argv[2] if len(sys.argv) > 2 else "maps/map-borders-1px.png"
    extract_1px_borders(src, dst)
