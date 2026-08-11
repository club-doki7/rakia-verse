#include <dos.h>
#include <dpmi.h>
#include <go32.h>
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

static int get_vesa_info(void);
static int get_mode_info(int mode);
static int find_vesa_mode(void);
static void set_vesa_bank(int bank);
static void set_rgb332_palette(void);

int svga_init(void) {
  __dpmi_regs r;
  int mode;

  if (get_vesa_info() != 0)
    return -1;

  mode = find_vesa_mode();
  if (mode < 0)
    return -1;

  /* Set the mode */
  r.x.ax = 0x4F02;
  r.x.bx = mode;
  __dpmi_int(0x10, &r);

  if (r.h.ah)
    return -1;

  current_bank = -1;
  set_rgb332_palette();
  return 0;
}

void svga_restore_text(void) {
  __dpmi_regs r;
  r.x.ax = 0x0003;
  __dpmi_int(0x10, &r);
}

void svga_draw_text(svga_buffer *buf,
                    text_buf const *txt_buf,
                    unsigned short x,
                    unsigned short y,
                    unsigned char const *text) {
  unsigned short cx = x, cy = y;
  unsigned char fg = 0xFF, bg = 0x00;
  unsigned int i;

  for (i = 0; text[i] != '\0'; i++) {
    unsigned char ch = text[i];

    if (ch >= 33 && ch <= 126) {
      unsigned char const *glyph = &txt_buf->asc_buf.chars[(ch - 33) * 16];
      int row, col;
      for (row = 0; row < 16; row++) {
        unsigned char bits = glyph[row];
        for (col = 0; col < 8; col++) {
          unsigned long off = (unsigned long)(cy + row) * 800 + (cx + col);
          if (cx + col < 800 && cy + row < 600)
            buf->localbuf[off] = (bits & (0x80 >> col)) ? bg : fg;
        }
      }
      cx += 8;
    } else if (ch == 32) {
      int row, col;
      for (row = 0; row < 16; row++) {
        for (col = 0; col < 8; col++) {
          unsigned long off = (unsigned long)(cy + row) * 800 + (cx + col);
          if (cx + col < 800 && cy + row < 600)
            buf->localbuf[off] = bg;
        }
      }
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
              unsigned long off = (unsigned long)(cy + row) * 800 + (cx + col);
              if (cx + col < 800 && cy + row < 600)
                buf->localbuf[off] = (bits & (0x8000 >> col)) ? bg : fg;
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
        for (row = 0; row < 16; row++) {
          for (col = 0; col < 8; col++) {
            unsigned long off = (unsigned long)(cy + row) * 800 + (cx + col);
            if (cx + col < 800 && cy + row < 600)
              buf->localbuf[off] = bg;
          }
        }
        cx += 8;
      }
    } else if (ch == '\f') {
      fg = text[++i];
    } else if (ch == '\v') {
      bg = text[++i];
    }
  }
}

void svga_flush(const svga_buffer *buf) {
  unsigned long offset = 0;
  unsigned long remaining = 800 * 600;
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
  unsigned short src_stride;

  if (clip_x + clip_w > bmp->width)
    clip_w = bmp->width - clip_x;
  if (clip_y + clip_h > bmp->height)
    clip_h = bmp->height - clip_y;

  if (bmp->rgb565) {
    /* RGB565 -> convert to RGB332 for the 8-bit framebuffer */
    src_stride = bmp->width * 2;
    for (row = 0; row < clip_h && y + row < 600; row++) {
      unsigned char const *src_row = bmp->pixels
                                     + (unsigned long)(clip_y + row) * src_stride
                                     + clip_x * 2;
      for (col = 0; col < clip_w && x + col < 800; col++) {
        unsigned short px = (unsigned short)src_row[col * 2]
                            | ((unsigned short)src_row[col * 2 + 1] << 8);
        unsigned char r = (px >> 11) & 0x1F;
        unsigned char g = (px >> 5) & 0x3F;
        unsigned char b = px & 0x1F;
        /* RGB332: 3 bits R, 3 bits G, 2 bits B */
        buf->localbuf[(unsigned long)(y + row) * 800 + (x + col)] =
            ((r >> 2) << 5) | ((g >> 3) << 2) | (b >> 3);
      }
    }
  } else {
    /* 1-bit: white on set bit, black otherwise */
    src_stride = (bmp->width + 7) / 8;
    for (row = 0; row < clip_h && y + row < 600; row++) {
      unsigned char const *src_row = bmp->pixels + (unsigned long)(clip_y + row) * src_stride;
      for (col = 0; col < clip_w && x + col < 800; col++) {
        unsigned short sx = clip_x + col;
        unsigned char bit = (src_row[sx / 8] >> (7 - (sx & 7))) & 1;
        buf->localbuf[(unsigned long)(y + row) * 800 + (x + col)] = bit ? 0xFF : 0x00;
      }
    }
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

/* Find 800x600 8bpp mode by enumerating the mode list */
static int find_vesa_mode(void) {
  unsigned long mode_ptr;
  unsigned short seg, off;
  unsigned short mode;
  long list_addr;

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
    if (mode_info.XResolution == 800 &&
        mode_info.YResolution == 600 &&
        mode_info.BitsPerPixel == 8)
      return mode;
  }

  return -1;
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
