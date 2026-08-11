#include <conio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "render.h"
#include "text.h"

int main(int argc, char **argv) {
  svga_mode_info modes[16];
  svga_buffer buf;
  int count;

  count = svga_detect(modes, 16, 0);
  if (count <= 0) {
    fprintf(stderr, "No supported SVGA modes found.\n");
    return 1;
  }

  if (svga_init(&buf, modes[0].mode_number) != 0) {
    fprintf(stderr, "svga_init failed.\n");
    return 1;
  }

  {
    txt_buf *tb = text_init();
    /* \f sets fg (R G B), \v sets bg (R G B) */
    static const unsigned char msg[] =
      "\f\xFF\xFF\xFF"           /* fg = white */
      "\v\x00\x00\x00"           /* bg = black */
      "Hello, world!\t(tab)\n"
      "The quick brown fox jumped over the lazy dog.\n"
      "ASCII: !\"#$%&'()*\n"
      "\f\xFF\x40\x40"           /* fg = red */
      "\v\xD0\xD0\x00"           /* bg = yellow */
      "\x80\x00\x80\x01\x80\x02\n"   /* cn_bufs[0] chars 0, 1, 2 */
      "\f\xFF\xFF\xFF\v\x00\x00\x00"
      "done.";

    svga_draw_text(&buf, tb, 100, 100, msg);
  }

  svga_flush(&buf);

  getch();
  svga_restore_text();
  free(buf.localbuf);
  return 0;
}
