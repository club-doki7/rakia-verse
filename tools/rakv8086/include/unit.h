#ifndef RAKV_UNIT_H
#define RAKV_UNIT_H

typedef enum attack_tags {
  ATCK_RANGED = 0x01,
  ATCK_MAGICAL = 0x02,
  ATCK_PRECISE = 0x04,
  ATCK_POISON = 0x08,
  ATCK_CHARGE = 0x10,
  ATCK_FSTRIKE = 0x20,
  ATCK_SLOW = 0x40,
  ATCK_BACKSTAB = 0x80
} attack_tags;

typedef enum damage_kinds {
  DMG_BLADE = 0,
  DMG_PIERCE = 1,
  DMG_IMPACT = 2,
  DMG_FIRE = 3,
  DMG_COLD = 4,
  DMG_ELECTRIC = 5,
  DMG_ACID = 6,
  DMG_POISON = 7,
  DMG_FORCE = 8,
} damage_kinds;

typedef struct attack_base {
  unsigned short tags;
  unsigned char strike;
  unsigned char damage;
  unsigned char k_damage;
  unsigned char name[16];
} attack_base;

typedef struct attack {
  unsigned char type;
  unsigned char strike;
  unsigned char damage;
  unsigned char k_damage;
  unsigned char name[16];
  struct attack *next;
} attack;

typedef struct unit_template {
  unsigned short id;
  unsigned short level;
  unsigned short max_hp;
  unsigned char defence[16];
  unsigned char resist[9];

  unsigned char name[16];
  unsigned short advance_to[3];
  unsigned char n_attacks;
  attack_base attacks[];
} unit_template;

typedef struct unit {
  unit_template *template;
  unsigned short level;
  unsigned short max_hp;
  unsigned char defence[16];
  unsigned char resist[9];

  unsigned short hp;
  unsigned short x;
  unsigned short y;

  attack *attacks;

  unsigned char name[16];
} unit;

#endif /* RAKV_UNIT_H */
