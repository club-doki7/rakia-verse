#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bitmap.h"
#include "text.h"

#define MAX_CN_FILES 10
#define CHARS_PER_ROW 32
#define ASC_CHAR_W 8
#define ASC_CHAR_H 16
#define CN_CHAR_W 16
#define CN_CHAR_H 16

static text_buf *tb = NULL;

static void load_ascii(asc_buf *asc);
static cn_buf *load_cn_file(const char *path);

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

static void load_ascii(asc_buf *asc) {
  bitmap *bm;
  int scanline, col, row, y, idx;

  bm = load_bmp("ascii.bmp");
  if (!bm)
    return;

  scanline = (bm->width + 7) / 8;

  for (idx = 0; idx < 94; idx++) {
    col = idx % CHARS_PER_ROW;
    row = idx / CHARS_PER_ROW;
    for (y = 0; y < ASC_CHAR_H; y++) {
      int img_y = row * ASC_CHAR_H + y;
      if (img_y >= bm->height) break;
      asc->chars[idx * ASC_CHAR_H + y] = bm->pixels[img_y * scanline + col];
    }
  }

  free(bm);
}

static cn_buf *load_cn_file(const char *path) {
  bitmap *bm;
  int scanline, rows, char_count;
  int col, row, y, idx;
  cn_buf *cn;

  bm = load_bmp(path);
  if (!bm)
    return NULL;

  scanline = (bm->width + 7) / 8;
  rows = bm->height / CN_CHAR_H;
  char_count = rows * CHARS_PER_ROW;

  cn = malloc(sizeof(cn_buf) + (unsigned long)char_count * 32);
  if (!cn) {
    free(bm);
    return NULL;
  }
  cn->char_count = char_count;

  for (idx = 0; idx < char_count; idx++) {
    col = idx % CHARS_PER_ROW;
    row = idx / CHARS_PER_ROW;
    for (y = 0; y < CN_CHAR_H; y++) {
      int img_y = row * CN_CHAR_H + y;
      int byte_off = col * 2;
      cn->chars[idx * 32 + y * 2]     = bm->pixels[img_y * scanline + byte_off];
      cn->chars[idx * 32 + y * 2 + 1] = bm->pixels[img_y * scanline + byte_off + 1];
    }
  }

  free(bm);
  return cn;
}

