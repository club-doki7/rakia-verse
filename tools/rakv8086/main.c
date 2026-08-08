#include <conio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "render.h"
#include "text.h"

static int load_bmp(const char *path, svga_buffer *buf) {
  FILE *f;
  unsigned long offset;
  int width, height, y;
  unsigned char header[54];

  f = fopen(path, "rb");
  if (!f)
    return -1;

  fread(header, 1, 54, f);
  offset = *(unsigned long *)(header + 10);
  width  = *(int *)(header + 18);
  height = *(int *)(header + 22);

  if (width != 800 || height != 600) {
    fclose(f);
    return -1;
  }

  /* Skip to pixel data, BMP is bottom-up */
  fseek(f, offset, SEEK_SET);
  for (y = 599; y >= 0; y--)
    fread(buf->localbuf + y * 800, 1, 800, f);

  fclose(f);
  return 0;
}

int main(int argc, char **argv) {
  const char *bmp_path = (argc > 1) ? argv[1] : "bliss.bmp";
  svga_buffer *buf = malloc(sizeof(svga_buffer));
  if (!buf)
    return 1;

  if (load_bmp(bmp_path, buf) != 0) {
    free(buf);
    return 1;
  }

  if (svga_init() != 0) {
    free(buf);
    return 1;
  }

  {
    text_buf *tb = text_init();
    /* \f sets fg, \v sets bg; \x80\x00~\x80\x02 = cn_bufs[0] chars 0-2 */
    static const unsigned char msg[] =
      "\f\xFF"           /* fg = white */
      "\v\x00"           /* bg = black */
      "Hello, world!\t(tab)\n"
      "The quick brown fox jumped over the lazy dog.\n"
      "ASCII: !\"#$%&'()*\n"
      "\f\xE0"           /* fg = red-ish (RGB332: 0xE0 = 111_000_00) */
      "\v\xD8"           /* bg = yellow-ish (RGB332: 0xD8 = 110_110_00) */
      "\x80\x00\x80\x01\x80\x02\n"   /* cn_bufs[0] chars 0, 1, 2 */
      "\f\xFF\v\x00"
      "done.";

    svga_draw_text(buf, tb, 100, 100, msg);
  }

  svga_flush(buf);

  getch();
  svga_restore_text();
  free(buf);
  return 0;
}
