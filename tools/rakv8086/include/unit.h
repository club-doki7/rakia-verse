#ifndef RAKV_UNIT_H
#define RAKV_UNIT_H

#include <stdint.h>

typedef enum UnitSpecial {
  US_None = 0,
  US_Regeneration4 = 0x01,
  US_Regeneration8 = 0x02,
  US_RecoverPoison = 0x04,
  US_Heal4 = 0x08,
  US_Heal8 = 0x10,
  US_CurePoison = 0x20,
  US_Leadership = 0x40,
  US_Skirmisher = 0x80,
  US_Steadfast = 0x100,
  US_Ambush = 0x200,
  US_Nightstalk = 0x400,
  US_Concealment = 0x800,
  US_Submerge = 0x1000,
  US_Illuminates = 0x2000,
  US_Feeding = 0x4000,

  US_CustomStart = 0x10000
} UnitSpecial;

typedef enum DamageKind {
  DK_Blade = 0,
  DK_Impact = 1,
  DK_Pierce = 2,
  DK_Fire = 3,
  DK_Cold = 4,
  DK_Lightning = 5,
  DK_Acid = 6,
  DK_Poison = 7,
  DK_Force = 8
} DamageKind;

typedef enum AttackSpecial {
  AS_None = 0,
  AS_Ranged = 0x01,
  AS_Slow = 0x02,
  AS_Poison = 0x04,
  AS_Magecraft = 0x08,
  AS_Marksman = 0x10,
  AS_Stunning = 0x20,
  AS_Daze = 0x40,
  AS_Reload = 0x80,
  AS_Firststrike = 0x100,
  AS_Backstab = 0x200,
  AS_Charge = 0x400,
  AS_Drain = 0x800,
  AS_Berserk = 0x1000,
  AS_Swarm = 0x2000,
  AS_Counter = 0x4000,

  AS_CustomStart = 0x10000
} AttackSpecial;

#define RAKV_INT_ATTACK_BASE \
  uint8_t displayId[15]; \
  uint8_t kDamage; \
  uint8_t damage; \
  uint8_t strike; \
  uint32_t special;

typedef struct AttackBase {
  RAKV_INT_ATTACK_BASE
} AttackBase;

typedef struct Attack {
  RAKV_INT_ATTACK_BASE
  struct Attack *next;
} Attack;

#define RAKV_INT_UNIT_BASE \
  uint8_t uid[15]; \
  uint8_t historyId[15]; \
  uint8_t name[15]; \
  uint8_t level; \
  uint16_t maxHealth; \
  uint32_t special;

typedef struct UnitBase {
  RAKV_INT_UNIT_BASE
  uint8_t nAttack;
  uint8_t nAdvancement;
  AttackBase *attacks;
  struct UnitBase *advancements;

  _Alignas(4) uint8_t buf[];
} UnitBase;

typedef struct Unit {
  RAKV_INT_UNIT_BASE
  uint16_t health;
  uint16_t xpToLevelup;
  Attack *attack;
} Unit;

#endif /* RAKV_UNIT_H */
