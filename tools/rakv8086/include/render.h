#ifndef RAKV8086_RENDER_H
#define RAKV8086_RENDER_H

#include "bitmap.h"
#include "text.h"

typedef struct svga_mode_info {
  unsigned short mode_number;
  unsigned short width;
  unsigned short height;
  unsigned char  bpp; /* 8, 16, or 24 */
} svga_mode_info;

typedef struct svga_buffer {
  unsigned short width;
  unsigned short height;
  unsigned char  bpp;          /* 8, 16, or 24 */
  unsigned char  bytes_per_px; /* 1, 2, or 3 */
  unsigned long  buf_size;     /* width * height * bytes_per_px */
  unsigned char  *localbuf;
} svga_buffer;

/* Enumerate VESA modes (8/16/24bpp) into caller-provided buffer.
   Returns count written. If count == bufsiz, call again with offset += count.
   Returns -1 on error. */
int  svga_detect(svga_mode_info *info, unsigned short bufsiz, unsigned short offset);

/* Initialize given mode. Allocates buf->localbuf. Returns 0 on success. */
int  svga_init(svga_buffer *buf, unsigned short mode_number);

void svga_restore_text(void);
void svga_flush(svga_buffer const *buf);

void svga_draw_text(svga_buffer *buf,
                    txt_buf const *txt_buf,
                    unsigned short x,
                    unsigned short y,
                    unsigned char const *text);

void svga_draw_bitmap(svga_buffer *buf,
                      bitmap const *bmp,
                      unsigned short x,
                      unsigned short y);
void svga_draw_bitmap_clip(svga_buffer *buf,
                           bitmap const *bmp,
                           unsigned short x,
                           unsigned short y,
                           unsigned short clip_x,
                           unsigned short clip_y,
                           unsigned short clip_w,
                           unsigned short clip_h);

#endif /* RAKV8086_RENDER_H */
