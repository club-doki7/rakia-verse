#!/usr/bin/env python3
"""王国历 (KC/BK) 与迁徙历 (AH/BH) 相互转换。

历法设定：
- 王国历一年 360 天，15 月 × 24 天；纪元前用 BK，纪元后用 KC，无 0 年。
- 迁徙历一年 343 天，7 月 × 49 天；纪元后用 AH，纪元前（外推）用 BH，无 0 年。
- 锚点：0001-01-01AH = 1372-08-23BK。

用法：
  python calendar_convert.py 1372-08-23BK   # 精确日期转换
  python calendar_convert.py 618BK          # 仅年份，输出对应年份范围
  python calendar_convert.py               # 无参数进入 stdio 交互模式
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass

KC_YEAR_DAYS = 360
KC_MONTH_DAYS = 24
KC_MONTHS = 15

AH_YEAR_DAYS = 343
AH_MONTH_DAYS = 49
AH_MONTHS = 7

# 0001-01-01AH 对应的王国历绝对天数（以 0001-01-01KC 为第 0 天）
AH_EPOCH_ABS = -1372 * KC_YEAR_DAYS + (8 - 1) * KC_MONTH_DAYS + (23 - 1)

KINGDOM_ERAS = ("KC", "BK")
HIJRI_ERAS = ("AH", "BH")


@dataclass(frozen=True)
class Date:
    era: str  # KC / BK / AH / BH
    year: int
    month: int
    day: int

    @property
    def is_kingdom(self) -> bool:
        return self.era in KINGDOM_ERAS

    def __str__(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}{self.era}"


DATE_RE = re.compile(
    r"^(\d+)(?:-(\d+)-(\d+))?\s*(BK|KC|AH|BH)$",
    re.IGNORECASE,
)


def parse(text: str) -> tuple[str, int, int | None, int | None]:
    """解析输入，返回 (era, year, month|None, day|None)。"""
    m = DATE_RE.match(text.strip())
    if not m:
        raise ValueError(
            f"无法解析：{text!r}（示例：1372-08-23BK、0001-01-01AH、618BK）"
        )
    year_s, month_s, day_s, era = m.groups()
    era = era.upper()
    year = int(year_s)
    if year < 1:
        raise ValueError("年份必须 >= 1（无 0 年）")
    if month_s is None:
        return era, year, None, None

    month, day = int(month_s), int(day_s)
    months, month_days = (
        (KC_MONTHS, KC_MONTH_DAYS) if era in KINGDOM_ERAS else (AH_MONTHS, AH_MONTH_DAYS)
    )
    if not 1 <= month <= months:
        raise ValueError(f"{era} 历月份须在 1~{months} 之间，得到 {month}")
    if not 1 <= day <= month_days:
        raise ValueError(f"{era} 历日须在 1~{month_days} 之间，得到 {day}")
    return era, year, month, day


def to_abs(era: str, year: int, month: int, day: int) -> int:
    """转为绝对天数（0001-01-01KC 为第 0 天）。"""
    if era in KINGDOM_ERAS:
        y = year - 1 if era == "KC" else -year
        return y * KC_YEAR_DAYS + (month - 1) * KC_MONTH_DAYS + (day - 1)
    y = year - 1 if era == "AH" else -year
    return AH_EPOCH_ABS + y * AH_YEAR_DAYS + (month - 1) * AH_MONTH_DAYS + (day - 1)


def abs_to_kingdom(abs_day: int) -> Date:
    q, r = divmod(abs_day, KC_YEAR_DAYS)
    era, year = ("KC", q + 1) if q >= 0 else ("BK", -q)
    return Date(era, year, r // KC_MONTH_DAYS + 1, r % KC_MONTH_DAYS + 1)


def abs_to_hijri(abs_day: int) -> Date:
    q, r = divmod(abs_day - AH_EPOCH_ABS, AH_YEAR_DAYS)
    era, year = ("AH", q + 1) if q >= 0 else ("BH", -q)
    return Date(era, year, r // AH_MONTH_DAYS + 1, r % AH_MONTH_DAYS + 1)


def convert(text: str) -> str:
    era, year, month, day = parse(text)
    kingdom_input = era in KINGDOM_ERAS
    to_other = abs_to_hijri if kingdom_input else abs_to_kingdom

    if month is not None:
        assert day is not None
        result = to_other(to_abs(era, year, month, day))
        return f"{Date(era, year, month, day)} = {result}"

    # 仅年份：给出该年首日与末日对应的日期范围
    months, month_days = (
        (KC_MONTHS, KC_MONTH_DAYS) if kingdom_input else (AH_MONTHS, AH_MONTH_DAYS)
    )
    first = to_other(to_abs(era, year, 1, 1))
    last = to_other(to_abs(era, year, months, month_days))
    if first.era == last.era and first.year == last.year:
        span = f"{first.year}{first.era}"
    else:
        span = f"{first.year}{first.era} ~ {last.year}{last.era}"
    return f"{year}{era} = {span}（{first} ~ {last}）"


def interactive() -> None:
    is_tty = sys.stdin.isatty()
    if is_tty:
        print("历法转换（王国历 <-> 迁徙历）。输入日期，如 1372-08-23BK 或 618BK；q 退出。")
    while True:
        try:
            line = input("> " if is_tty else "")
        except EOFError:
            break
        line = line.strip()
        if not line:
            continue
        if line.lower() in ("q", "quit", "exit"):
            break
        try:
            print(convert(line))
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)


def main(argv: list[str]) -> int:
    if not argv:
        interactive()
        return 0
    status = 0
    for arg in argv:
        try:
            print(convert(arg))
        except ValueError as e:
            print(f"错误：{e}", file=sys.stderr)
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
