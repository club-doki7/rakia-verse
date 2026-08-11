#include <conio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "render.h"
#include "text.h"

int main(int argc, char **argv) {
  svga_mode_info modes[16];
  int count, offset = 0, i;

  printf("Available SVGA modes:\n");
  printf("  MODE   WIDTH  HEIGHT  BPP\n");

  do {
    count = svga_detect(modes, 16, offset);
    if (count < 0) {
      fprintf(stderr, "VESA detection failed.\n");
      return 1;
    }
    for (i = 0; i < count; i++) {
      printf("  0x%04X  %4u   %4u    %2u\n",
             modes[i].mode_number,
             modes[i].width,
             modes[i].height,
             modes[i].bpp);
    }
    offset += count;
    getch();
  } while (count == 16);

  if (offset == 0)
    printf("  (none)\n");

  getch();
  return 0;
}
