#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "text.h"

#define MAX_CN_FILES 10
#define CHARS_PER_ROW 32
#define ASC_CHAR_W 8
#define ASC_CHAR_H 16
#define CN_CHAR_W 16
#define CN_CHAR_H 16

static text_buf *tb = NULL;

/* Read 1-bit BMP pixel data into a top-down buffer. Returns height, or -1. */
static int read_bmp_1bit(const char *path,
                         int *out_width,
                         unsigned char **out_pixels) {
  FILE *f;
  unsigned char header[62];
  unsigned long offset;
  int width, height, y;
  int scanline_bytes, padded_scanline;
  unsigned char *pixels;

  f = fopen(path, "rb");
  if (!f)
    return -1;

  if (fread(header, 1, 62, f) < 54) {
    fclose(f);
    return -1;
  }

  offset = *(unsigned long *)(header + 10);
  width  = *(int *)(header + 18);
  height = *(int *)(header + 22);

  if (width <= 0 || height <= 0) {
    fclose(f);
    return -1;
  }

  /* 1-bit scanline: width bits, padded to 4 bytes */
  scanline_bytes = (width + 7) / 8;
  padded_scanline = (scanline_bytes + 3) & ~3;

  pixels = malloc(scanline_bytes * height);
  if (!pixels) {
    fclose(f);
    return -1;
  }

  fseek(f, offset, SEEK_SET);
  /* BMP is bottom-up */
  for (y = height - 1; y >= 0; y--) {
    fread(pixels + y * scanline_bytes, 1, scanline_bytes, f);
    if (padded_scanline > scanline_bytes)
      fseek(f, padded_scanline - scanline_bytes, SEEK_CUR);
  }

  fclose(f);
  *out_width = width;
  *out_pixels = pixels;
  return height;
}

static void load_ascii(asc_buf *asc) {
  unsigned char *pixels;
  int width, height, scanline;
  int col, row, y, idx;

  height = read_bmp_1bit("ascii.bmp", &width, &pixels);
  if (height < 0)
    return;

  scanline = (width + 7) / 8;

  for (idx = 0; idx < 94; idx++) {
    col = idx % CHARS_PER_ROW;
    row = idx / CHARS_PER_ROW;
    for (y = 0; y < ASC_CHAR_H; y++) {
      int img_y = row * ASC_CHAR_H + y;
      if (img_y >= height) break;
      asc->chars[idx * ASC_CHAR_H + y] = pixels[img_y * scanline + col];
    }
  }

  free(pixels);
}

static cn_buf *load_cn_file(const char *path) {
  unsigned char *pixels;
  int width, height, scanline;
  int rows, char_count;
  int col, row, y, idx;
  cn_buf *cn;

  height = read_bmp_1bit(path, &width, &pixels);
  if (height < 0)
    return NULL;

  scanline = (width + 7) / 8;
  rows = height / CN_CHAR_H;
  char_count = rows * CHARS_PER_ROW;

  cn = malloc(sizeof(cn_buf) + (unsigned long)char_count * 32);
  if (!cn) {
    free(pixels);
    return NULL;
  }
  cn->char_count = char_count;

  for (idx = 0; idx < char_count; idx++) {
    col = idx % CHARS_PER_ROW;
    row = idx / CHARS_PER_ROW;
    for (y = 0; y < CN_CHAR_H; y++) {
      int img_y = row * CN_CHAR_H + y;
      int byte_off = col * 2;
      cn->chars[idx * 32 + y * 2]     = pixels[img_y * scanline + byte_off];
      cn->chars[idx * 32 + y * 2 + 1] = pixels[img_y * scanline + byte_off + 1];
    }
  }

  free(pixels);
  return cn;
}

text_buf *text_init(void) {
  cn_buf *cn_files[MAX_CN_FILES];
  int cn_count = 0;
  int i;
  char path[16];

  for (i = 0; i < MAX_CN_FILES; i++) {
    sprintf(path, "cn%03d.bmp", i);
    cn_files[i] = load_cn_file(path);
    if (!cn_files[i])
      break;
    cn_count++;
  }

  tb = malloc(sizeof(text_buf) + (unsigned long)cn_count * sizeof(cn_buf *));
  if (!tb)
    return NULL;

  memset(&tb->asc_buf, 0, sizeof(asc_buf));
  tb->cnt_cn_buf = cn_count;
  for (i = 0; i < cn_count; i++)
    tb->cn_bufs[i] = cn_files[i];

  load_ascii(&tb->asc_buf);
  return tb;
}
