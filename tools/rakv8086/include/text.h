#ifndef RAKV8086_TEXT_H
#define RAKV8086_TEXT_H

typedef struct asc_buf {
  /* 94 characters, 8*16 pixels each, 1bit per pixel; 16 bytes per character */
  unsigned char chars[94 * 16];
} asc_buf;

typedef struct cn_buf {
  /* N-characters, 16*16 pixels each, 1bit per pixel; 32 bytes per character */
  unsigned short char_count;
  unsigned char chars[];
} cn_buf;

typedef struct txt_buf {
  unsigned short cnt_cn_buf;
  asc_buf asc_buf;
  cn_buf *cn_bufs[];
} txt_buf;

txt_buf *text_init(void);

#endif /* RAKV8086_TEXT_H */
