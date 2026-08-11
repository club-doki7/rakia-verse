#ifndef RAKV8086_BITMAP_H
#define RAKV8086_BITMAP_H

typedef struct bitmap {
  unsigned short width;
  unsigned short height;
  unsigned char  bpp; /* 1, 4, 8, 16, 24, or 32 */
  unsigned char  pixels[];
} bitmap;

bitmap *load_bmp(const char *path);

#endif /* RAKV8086_BITMAP_H */
