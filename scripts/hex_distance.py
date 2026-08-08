#!/usr/bin/env python3
"""
计算 odd-r 坐标系下六边形格子之间的距离

odd-r (offset coordinates with odd rows offset right) 是一种六边形网格坐标系统，
其中奇数行向右偏移半个格子。

本脚本适用于尖头朝上（pointy-top）的六边形网格。
"""

import argparse
import math
from typing import Tuple


def hex_center_spacing(side: float) -> float:
    """尖头朝上六边形相邻格心间距，即对边距 sqrt(3) * 边长"""
    return math.sqrt(3) * side


def oddr_to_cube(col: int, row: int) -> Tuple[int, int, int]:
    """
    将 odd-r 坐标转换为 cube 坐标

    Args:
        col: 列坐标
        row: 行坐标

    Returns:
        (x, y, z) cube 坐标，满足 x + y + z = 0
    """
    x = col - (row - (row & 1)) // 2
    z = row
    y = -x - z
    return (x, y, z)


def cube_distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> int:
    """
    计算两个 cube 坐标之间的距离

    Args:
        a: 第一个 cube 坐标 (x, y, z)
        b: 第二个 cube 坐标 (x, y, z)

    Returns:
        两个坐标之间的距离（格子数）
    """
    return (abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])) // 2


def oddr_distance(col1: int, row1: int, col2: int, row2: int) -> int:
    """
    计算两个 odd-r 坐标之间的距离

    Args:
        col1: 第一个格子的列坐标
        row1: 第一个格子的行坐标
        col2: 第二个格子的列坐标
        row2: 第二个格子的行坐标

    Returns:
        两个格子之间的距离（格子数）
    """
    cube1 = oddr_to_cube(col1, row1)
    cube2 = oddr_to_cube(col2, row2)
    return cube_distance(cube1, cube2)


def main():
    parser = argparse.ArgumentParser(
        description='计算 odd-r 坐标系下两个六边形格子之间的距离'
    )
    parser.add_argument('col1', type=int, help='第一个格子的列坐标')
    parser.add_argument('row1', type=int, help='第一个格子的行坐标')
    parser.add_argument('col2', type=int, help='第二个格子的列坐标')
    parser.add_argument('row2', type=int, help='第二个格子的行坐标')
    parser.add_argument('-s', '--hex-side', type=float, default=40.0,
                        help='六角格的边长（km），默认为 40km')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='显示详细信息（包括 cube 坐标）')

    args = parser.parse_args()

    distance = oddr_distance(args.col1, args.row1, args.col2, args.row2)
    spacing = hex_center_spacing(args.hex_side)
    actual_distance = distance * spacing

    if args.verbose:
        cube1 = oddr_to_cube(args.col1, args.row1)
        cube2 = oddr_to_cube(args.col2, args.row2)
        print(f"格子1 odd-r: ({args.col1}, {args.row1}) -> cube: {cube1}")
        print(f"格子2 odd-r: ({args.col2}, {args.row2}) -> cube: {cube2}")
        print(f"边长: {args.hex_side:g} km, 格心间距: {spacing:.6f} km")
        print(f"格子距离: {distance}")
        print(f"实际距离: {actual_distance:.1f} km")
    else:
        print(f"{distance} ({actual_distance:.1f} km)")


if __name__ == '__main__':
    main()
