#ifndef RAKV8086_RENDER_H
#define RAKV8086_RENDER_H

#include "bitmap.h"
#include "text.h"

typedef struct svga_buffer {
  /* 256 colors on a 800 * 600 screen, requires SVGA mode 0x13 */
  unsigned char localbuf[800 * 600];
} svga_buffer;

int  svga_init(void);
void svga_restore_text(void);
void svga_flush(svga_buffer const* buf);

void svga_draw_text(svga_buffer *buf,
                    txt_buf const* txt_buf,
                    unsigned short x,
                    unsigned short y,
                    unsigned char const *text);

void svga_draw_bitmap(svga_buffer *buf,
                      bitmap const* bmp,
                      unsigned short x,
                      unsigned short y);
void svga_draw_bitmap_clip(svga_buffer *buf,
                           bitmap const* bmp,
                           unsigned short x,
                           unsigned short y,
                           unsigned short clip_x,
                           unsigned short clip_y,
                           unsigned short clip_w,
                           unsigned short clip_h);

#endif /* RAKV8086_RENDER_H */
