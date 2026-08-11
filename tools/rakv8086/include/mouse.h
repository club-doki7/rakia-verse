#ifndef RAKV8086_MOUSE_H
#define RAKV8086_MOUSE_H

typedef enum {
  MOUSE_LEFT = 0x01,
  MOUSE_RIGHT = 0x02
} mouse_btn;

typedef struct mouse_stat {
  unsigned short x;
  unsigned short y;
  unsigned char buttons;
} mouse_stat;

int mouse_init(unsigned short x_max, unsigned short y_max);
void mouse_get_stat(mouse_stat *stat);

#endif /* RAKV8086_MOUSE_H */
