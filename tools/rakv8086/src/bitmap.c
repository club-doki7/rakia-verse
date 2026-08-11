#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bitmap.h"

bitmap *load_bmp(const char *path) {
  FILE *f;
  unsigned char header[54];
  unsigned long offset;
  int width, height, bpp, row_stride, y;
  bitmap *bm;
  unsigned long pixel_size;

  f = fopen(path, "rb");
  if (!f)
    return NULL;

  if (fread(header, 1, 54, f) != 54 || header[0] != 'B' || header[1] != 'M') {
    fclose(f);
    return NULL;
  }

  offset = *(unsigned long *)(header + 10);
  width  = *(int *)(header + 18);
  height = *(int *)(header + 22);
  bpp    = *(unsigned short *)(header + 28);

  if (width <= 0 || height <= 0) {
    fclose(f);
    return NULL;
  }

  if (bpp == 1) {
    row_stride = (width + 7) / 8;
  } else if (bpp == 4) {
    row_stride = (width + 1) / 2;
  } else if (bpp == 8 || bpp == 16 || bpp == 24 || bpp == 32) {
    row_stride = width * (bpp / 8);
  } else {
    fclose(f);
    return NULL;
  }
  pixel_size = (unsigned long)row_stride * height;

  bm = malloc(sizeof(bitmap) + pixel_size);
  if (!bm) {
    fclose(f);
    return NULL;
  }

  bm->width  = (unsigned short)width;
  bm->height = (unsigned short)height;
  bm->bpp    = (unsigned char)bpp;

  /* BMP rows are padded to 4 bytes and stored bottom-up */
  {
    int bmp_row_pad = (4 - (row_stride % 4)) % 4;
    int bmp_row_size = row_stride + bmp_row_pad;
    unsigned char *row_buf = malloc(bmp_row_size);
    if (!row_buf) {
      free(bm);
      fclose(f);
      return NULL;
    }

    fseek(f, offset, SEEK_SET);
    for (y = height - 1; y >= 0; y--) {
      if (fread(row_buf, 1, bmp_row_size, f) != (size_t)bmp_row_size) {
        free(row_buf);
        free(bm);
        fclose(f);
        return NULL;
      }
      memcpy(bm->pixels + (unsigned long)y * row_stride, row_buf, row_stride);
    }
    free(row_buf);
  }

  fclose(f);
  return bm;
}
