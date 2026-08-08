"""Convert an image to 800x600 8-bit indexed BMP with RGB332 palette."""
import sys
import struct
import cv2
import numpy as np

if len(sys.argv) < 2:
    print(f"Usage: {sys.argv[0]} <input_image> [output_file]")
    sys.exit(1)

src = cv2.imread(sys.argv[1])
if src is None:
    print("Failed to read image")
    sys.exit(1)

img = cv2.resize(src, (800, 600), interpolation=cv2.INTER_AREA)
b, g, r = img[:, :, 0], img[:, :, 1], img[:, :, 2]
pixels = (((r >> 5) << 5) | ((g >> 5) << 2) | (b >> 6)).astype(np.uint8)

# BMP with 8bpp needs rows padded to 4 bytes; 800 is already divisible by 4
width, height = 800, 600
row_size = width
palette_size = 256 * 4
data_offset = 14 + 40 + palette_size
file_size = data_offset + row_size * height

out_path = sys.argv[2] if len(sys.argv) > 2 else "dosbox_c/bliss.bmp"
with open(out_path, "wb") as f:
    # BITMAPFILEHEADER
    f.write(struct.pack("<2sIHHI", b"BM", file_size, 0, 0, data_offset))
    # BITMAPINFOHEADER
    f.write(struct.pack("<IiiHHIIiiII", 40, width, height, 1, 8, 0,
                        row_size * height, 0, 0, 256, 0))
    # Palette (BGRA)
    for i in range(256):
        pr = ((i >> 5) & 7) * 255 // 7
        pg = ((i >> 2) & 7) * 255 // 7
        pb = (i & 3) * 255 // 3
        f.write(struct.pack("BBBB", pb, pg, pr, 0))
    # Pixel data (BMP is bottom-up)
    for row in reversed(range(height)):
        f.write(pixels[row].tobytes())

print(f"Written {out_path} ({width}x{height}, 8bpp indexed)")
