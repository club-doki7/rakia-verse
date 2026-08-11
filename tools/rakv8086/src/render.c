#include <dos.h>
#include <dpmi.h>
#include <go32.h>
#include <stdlib.h>
#include <sys/farptr.h>
#include <sys/movedata.h>
#include <string.h>
#include "bitmap.h"
#include "render.h"

typedef struct __attribute__((packed)) {
  char           VESASignature[4];
  unsigned short VESAVersion;
  unsigned long  OEMStringPtr;
  unsigned char  Capabilities[4];
  unsigned long  VideoModePtr;
  unsigned short TotalMemory;
  unsigned char  Reserved[236];
  unsigned char  OemData[256];
} VESA_INFO;

typedef struct __attribute__((packed)) {
  unsigned short ModeAttributes;
  unsigned char  WinAAttributes;
  unsigned char  WinBAttributes;
  unsigned short WinGranularity;
  unsigned short WinSize;
  unsigned short WinASegment;
  unsigned short WinBSegment;
  unsigned long  WinFuncPtr;
  unsigned short BytesPerScanLine;
  unsigned short XResolution;
  unsigned short YResolution;
  unsigned char  XCharSize;
  unsigned char  YCharSize;
  unsigned char  NumberOfPlanes;
  unsigned char  BitsPerPixel;
  unsigned char  NumberOfBanks;
  unsigned char  MemoryModel;
  unsigned char  BankSize;
  unsigned char  NumberOfImagePages;
  unsigned char  Reserved1;
  unsigned char  RedMaskSize;
  unsigned char  RedFieldPosition;
  unsigned char  GreenMaskSize;
  unsigned char  GreenFieldPosition;
  unsigned char  BlueMaskSize;
  unsigned char  BlueFieldPosition;
  unsigned char  RsvdMaskSize;
  unsigned char  RsvdFieldPosition;
  unsigned char  DirectColorModeInfo;
  unsigned long  PhysBasePtr;
  unsigned long  OffScreenMemOffset;
  unsigned short OffScreenMemSize;
  unsigned char  Reserved2[206];
} MODE_INFO;

static VESA_INFO vesa_info;
static MODE_INFO mode_info;
static int current_bank = -1;

static int  get_vesa_info(void);
static int  get_mode_info(int mode);
static void set_vesa_bank(int bank);
static void set_rgb332_palette(void);
/* Write a pixel into localbuf at (px, py), converting r/g/b to native bpp */
static void put_pixel(svga_buffer *buf,
                      unsigned short px, unsigned short py,
                      unsigned char r, unsigned char g, unsigned char b);

/* --- Public API --------------------------------------------------------- */

int svga_detect(svga_mode_info *info, unsigned short bufsiz, unsigned short offset) {
  unsigned long mode_ptr;
  unsigned short seg, off;
  unsigned short mode;
  long list_addr;
  unsigned short skipped = 0, written = 0;

  if (get_vesa_info() != 0)
    return -1;

  mode_ptr = vesa_info.VideoModePtr;
  seg = (mode_ptr >> 16) & 0xFFFF;
  off = mode_ptr & 0xFFFF;
  list_addr = (long)seg * 16 + off;

  for (;;) {
    mode = _farpeekw(_dos_ds, list_addr);
    if (mode == 0xFFFF)
      break;
    list_addr += 2;

    if (get_mode_info(mode) != 0)
      continue;

    if ((mode_info.BitsPerPixel == 8 ||
         mode_info.BitsPerPixel == 16 ||
         mode_info.BitsPerPixel == 24) &&
        mode_info.NumberOfPlanes == 1 &&
        (mode_info.ModeAttributes & 0x01)) {
      if (skipped < offset) {
        skipped++;
        continue;
      }
      if (written >= bufsiz)
        return written;
      info[written].mode_number = mode;
      info[written].width  = mode_info.XResolution;
      info[written].height = mode_info.YResolution;
      info[written].bpp    = mode_info.BitsPerPixel;
      written++;
    }
  }

  return written;
}

int svga_init(svga_buffer *buf, unsigned short mode_number) {
  __dpmi_regs r;

  if (get_vesa_info() != 0)
    return -1;

  if (get_mode_info(mode_number) != 0)
    return -1;

  r.x.ax = 0x4F02;
  r.x.bx = mode_number;
  __dpmi_int(0x10, &r);

  if (r.h.ah)
    return -1;

  current_bank = -1;

  buf->width       = mode_info.XResolution;
  buf->height      = mode_info.YResolution;
  buf->bpp         = mode_info.BitsPerPixel;
  buf->bytes_per_px = buf->bpp / 8;
  buf->buf_size    = (unsigned long)buf->width * buf->height * buf->bytes_per_px;
  buf->localbuf    = (unsigned char *)malloc(buf->buf_size);
  if (!buf->localbuf)
    return -1;
  memset(buf->localbuf, 0, buf->buf_size);

  if (buf->bpp == 8)
    set_rgb332_palette();

  return 0;
}

void svga_restore_text(void) {
  __dpmi_regs r;
  r.x.ax = 0x0003;
  __dpmi_int(0x10, &r);
}

void svga_flush(svga_buffer const *buf) {
  unsigned long offset = 0;
  unsigned long remaining = buf->buf_size;
  unsigned long gran = (unsigned long)mode_info.WinGranularity * 1024;
  unsigned long winsize = (unsigned long)mode_info.WinSize * 1024;
  int bank = 0;

  while (remaining > 0) {
    unsigned long chunk = remaining;
    if (chunk > winsize)
      chunk = winsize;

    set_vesa_bank(bank);
    dosmemput(buf->localbuf + offset, chunk, 0xA0000);

    offset += chunk;
    remaining -= chunk;
    bank += winsize / gran;
  }
}

void svga_draw_text(svga_buffer *buf,
                    txt_buf const *txt_buf,
                    unsigned short x,
                    unsigned short y,
                    unsigned char const *text) {
  unsigned short cx = x, cy = y;
  unsigned char fg_r = 0xFF, fg_g = 0xFF, fg_b = 0xFF;
  unsigned char bg_r = 0x00, bg_g = 0x00, bg_b = 0x00;
  unsigned int i;

  for (i = 0; text[i] != '\0'; i++) {
    unsigned char ch = text[i];

    if (ch >= 33 && ch <= 126) {
      unsigned char const *glyph = &txt_buf->asc_buf.chars[(ch - 33) * 16];
      int row, col;
      for (row = 0; row < 16; row++) {
        unsigned char bits = glyph[row];
        for (col = 0; col < 8; col++) {
          if (bits & (0x80 >> col))
            put_pixel(buf, cx + col, cy + row, bg_r, bg_g, bg_b);
          else
            put_pixel(buf, cx + col, cy + row, fg_r, fg_g, fg_b);
        }
      }
      cx += 8;
    } else if (ch == 32) {
      int row, col;
      for (row = 0; row < 16; row++)
        for (col = 0; col < 8; col++)
          put_pixel(buf, cx + col, cy + row, bg_r, bg_g, bg_b);
      cx += 8;
    } else if (ch >= 128) {
      unsigned short c_page = (ch >> 3) & 0x0F;
      unsigned short c_idx = (((unsigned short)ch << 8) | text[i + 1]) & 0x07FF;
      cn_buf const *page;
      i++;
      if (c_page < txt_buf->cnt_cn_buf) {
        page = txt_buf->cn_bufs[c_page];
        if (page && c_idx < page->char_count) {
          unsigned char const *glyph = &page->chars[c_idx * 32];
          int row, col;
          for (row = 0; row < 16; row++) {
            unsigned short bits = ((unsigned short)glyph[row * 2] << 8) | glyph[row * 2 + 1];
            for (col = 0; col < 16; col++) {
              if (bits & (0x8000 >> col))
                put_pixel(buf, cx + col, cy + row, bg_r, bg_g, bg_b);
              else
                put_pixel(buf, cx + col, cy + row, fg_r, fg_g, fg_b);
            }
          }
        }
      }
      cx += 16;
    } else if (ch == '\n') {
      cx = x;
      cy += 16;
    } else if (ch == '\t') {
      int s;
      for (s = 0; s < 4; s++) {
        int row, col;
        for (row = 0; row < 16; row++)
          for (col = 0; col < 8; col++)
            put_pixel(buf, cx + col, cy + row, bg_r, bg_g, bg_b);
        cx += 8;
      }
    } else if (ch == '\f') {
      fg_r = text[++i];
      fg_g = text[++i];
      fg_b = text[++i];
    } else if (ch == '\v') {
      bg_r = text[++i];
      bg_g = text[++i];
      bg_b = text[++i];
    }
  }
}

void svga_draw_bitmap(svga_buffer *buf,
                      bitmap const *bmp,
                      unsigned short x,
                      unsigned short y) {
  svga_draw_bitmap_clip(buf, bmp, x, y, 0, 0, bmp->width, bmp->height);
}

void svga_draw_bitmap_clip(svga_buffer *buf,
                           bitmap const *bmp,
                           unsigned short x,
                           unsigned short y,
                           unsigned short clip_x,
                           unsigned short clip_y,
                           unsigned short clip_w,
                           unsigned short clip_h) {
  unsigned short row, col;

  if (clip_x + clip_w > bmp->width)
    clip_w = bmp->width - clip_x;
  if (clip_y + clip_h > bmp->height)
    clip_h = bmp->height - clip_y;

  switch (bmp->bpp) {
  case 1: {
    unsigned short src_stride = (bmp->width + 7) / 8;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels + (unsigned long)(clip_y + row) * src_stride;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned short sx = clip_x + col;
        unsigned char bit = (src_row[sx / 8] >> (7 - (sx & 7))) & 1;
        put_pixel(buf, x + col, y + row, bit ? 0xFF : 0, bit ? 0xFF : 0, bit ? 0xFF : 0);
      }
    }
    break;
  }
  case 4: {
    unsigned short src_stride = (bmp->width + 1) / 2;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels + (unsigned long)(clip_y + row) * src_stride;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned short sx = clip_x + col;
        unsigned char nibble = (sx & 1)
            ? (src_row[sx / 2] & 0x0F)
            : (src_row[sx / 2] >> 4);
        unsigned char v = nibble * 17; /* expand 4-bit to 8-bit */
        put_pixel(buf, x + col, y + row, v, v, v);
      }
    }
    break;
  }
  case 8: {
    unsigned short src_stride = bmp->width;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels + (unsigned long)(clip_y + row) * src_stride + clip_x;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned char v = src_row[col];
        put_pixel(buf, x + col, y + row, v, v, v);
      }
    }
    break;
  }
  case 16: {
    unsigned short src_stride = bmp->width * 2;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels
                                     + (unsigned long)(clip_y + row) * src_stride
                                     + clip_x * 2;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned short px = (unsigned short)src_row[col * 2]
                          | ((unsigned short)src_row[col * 2 + 1] << 8);
        unsigned char r = ((px >> 11) & 0x1F) << 3;
        unsigned char g = ((px >> 5) & 0x3F) << 2;
        unsigned char b = (px & 0x1F) << 3;
        put_pixel(buf, x + col, y + row, r, g, b);
      }
    }
    break;
  }
  case 24: {
    unsigned short src_stride = bmp->width * 3;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels
                                     + (unsigned long)(clip_y + row) * src_stride
                                     + clip_x * 3;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned char b = src_row[col * 3];
        unsigned char g = src_row[col * 3 + 1];
        unsigned char r = src_row[col * 3 + 2];
        put_pixel(buf, x + col, y + row, r, g, b);
      }
    }
    break;
  }
  case 32: {
    unsigned short src_stride = bmp->width * 4;
    for (row = 0; row < clip_h && y + row < buf->height; row++) {
      unsigned char const *src_row = bmp->pixels
                                     + (unsigned long)(clip_y + row) * src_stride
                                     + clip_x * 4;
      for (col = 0; col < clip_w && x + col < buf->width; col++) {
        unsigned char b = src_row[col * 4];
        unsigned char g = src_row[col * 4 + 1];
        unsigned char r = src_row[col * 4 + 2];
        /* alpha (src_row[col*4+3]) ignored */
        put_pixel(buf, x + col, y + row, r, g, b);
      }
    }
    break;
  }
  }
}

/* --- Static implementations --------------------------------------------- */

static void put_pixel(svga_buffer *buf,
                      unsigned short px, unsigned short py,
                      unsigned char r, unsigned char g, unsigned char b) {
  unsigned long off;
  if (px >= buf->width || py >= buf->height) return;
  off = ((unsigned long)py * buf->width + px) * buf->bytes_per_px;

  switch (buf->bpp) {
  case 8:
    buf->localbuf[off] = ((r >> 5) << 5) | ((g >> 5) << 2) | (b >> 6);
    break;
  case 16: {
    unsigned short c = ((unsigned short)(r >> 3) << 11)
                     | ((unsigned short)(g >> 2) << 5)
                     | (b >> 3);
    buf->localbuf[off]     = c & 0xFF;
    buf->localbuf[off + 1] = c >> 8;
    break;
  }
  case 24:
    buf->localbuf[off]     = b;
    buf->localbuf[off + 1] = g;
    buf->localbuf[off + 2] = r;
    break;
  }
}

static int get_vesa_info(void) {
  __dpmi_regs r;
  long dosbuf = __tb & 0xFFFFF;

  dosmemput("VBE2", 4, dosbuf);

  r.x.ax = 0x4F00;
  r.x.di = dosbuf & 0xF;
  r.x.es = (dosbuf >> 4) & 0xFFFF;
  __dpmi_int(0x10, &r);

  if (r.h.ah)
    return -1;

  dosmemget(dosbuf, sizeof(VESA_INFO), &vesa_info);

  if (strncmp(vesa_info.VESASignature, "VESA", 4) != 0)
    return -1;

  return 0;
}

static int get_mode_info(int mode) {
  __dpmi_regs r;
  long dosbuf = __tb & 0xFFFFF;

  r.x.ax = 0x4F01;
  r.x.cx = mode;
  r.x.di = dosbuf & 0xF;
  r.x.es = (dosbuf >> 4) & 0xFFFF;
  __dpmi_int(0x10, &r);

  if (r.h.ah)
    return -1;

  dosmemget(dosbuf, sizeof(MODE_INFO), &mode_info);
  return 0;
}

static void set_vesa_bank(int bank) {
  __dpmi_regs r;
  if (bank == current_bank)
    return;
  current_bank = bank;
  r.x.ax = 0x4F05;
  r.x.bx = 0;
  r.x.dx = bank;
  __dpmi_int(0x10, &r);
}

static void set_rgb332_palette(void) {
  int i;
  for (i = 0; i < 256; i++) {
    outportb(0x3C8, i);
    outportb(0x3C9, ((i >> 5) & 7) * 9);
    outportb(0x3C9, ((i >> 2) & 7) * 9);
    outportb(0x3C9, (i & 3) * 21);
  }
}
