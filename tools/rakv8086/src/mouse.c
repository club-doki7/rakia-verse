#include <dos.h>
#include <dpmi.h>

#include "mouse.h"

int mouse_init(unsigned short x_max, unsigned short y_max) {
  __dpmi_regs regs;
  regs.x.ax = 0x0000;
  __dpmi_int(0x33, &regs);
  if (regs.x.ax == 0) return 0;
  regs.x.ax = 0x0007;
  regs.x.cx = 0;
  regs.x.dx = x_max;
  __dpmi_int(0x33, &regs);
  regs.x.ax = 0x0008;
  regs.x.cx = 0;
  regs.x.dx = y_max;
  __dpmi_int(0x33, &regs);
  return 1;
}

void mouse_get_stat(mouse_stat *stat) {
  __dpmi_regs regs;
  regs.x.ax = 0x0003;
  __dpmi_int(0x33, &regs);
  stat->buttons = regs.h.bl;
  stat->x = regs.x.cx;
  stat->y = regs.x.dx;
}
