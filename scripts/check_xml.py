#!/usr/bin/env python3
"""
XML 格式检查与字数统计脚本
用于 rakia-verse 项目，检查所有 XML 文件的格式合法性并统计字数。

用法:
    python check_xml.py [目录路径或文件路径]
    默认扫描当前工作目录下的所有 .xml 文件。
    如果指定的是单个 .xml 文件，则只检查该文件。

输出:
    - 每个文件的格式检查结果（通过 / 失败 + 错误信息）
    - 每个文件的字数统计（中文字符数、英文单词数、总字数）
    - 全局汇总
"""

import os
import re
import sys
from xml.etree import ElementTree as ET

# 强制标准输出和标准错误使用 UTF-8 编码
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# ─── 格式检查 ────────────────────────────────────────────────────────────────

def check_xml_wellformed(filepath: str) -> tuple[bool, str]:
    """
    检查 XML 文件是否格式良好 (well-formed)。
    返回 (是否通过, 错误信息或 "OK")。
    """
    try:
        ET.parse(filepath)
        return True, "OK"
    except ET.ParseError as e:
        return False, f"ParseError: {e}"
    except Exception as e:
        return False, f"Error: {e}"


# ─── 字数统计 ────────────────────────────────────────────────────────────────

def extract_text(filepath: str) -> str:
    """从 XML 文件中提取所有文本内容（含注释中的文本）。"""
    text_parts = []

    # 提取正文文本
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for elem in root.iter():
            if elem.text:
                text_parts.append(elem.text)
            if elem.tail:
                text_parts.append(elem.tail)
    except ET.ParseError:
        pass  # 格式有误的文件跳过正文提取

    # 提取 XML 注释中的文本
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        comments = re.findall(r"<!--(.*?)-->", content, re.DOTALL)
        text_parts.extend(comments)
    except Exception:
        pass

    return "\n".join(text_parts)


def count_words(text: str) -> dict[str, int]:
    """
    统计文本字数。
    - chinese: 中文字符数（每个汉字算 1 字）
    - english: 英文单词数（连续字母序列算 1 词）
    - total: chinese + english
    """
    # 中文字符（CJK 统一表意文字）
    chinese_chars = re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text)
    chinese_count = len(chinese_chars)

    # 移除中文字符后统计英文单词
    text_no_cjk = re.sub(r"[\u4e00-\u9fff\u3400-\u4dbf]", " ", text)
    english_words = re.findall(r"[a-zA-Z]+(?:'[a-zA-Z]+)*", text_no_cjk)
    english_count = len(english_words)

    return {
        "chinese": chinese_count,
        "english": english_count,
        "total": chinese_count + english_count,
    }


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def find_xml_files(root_dir: str) -> list[str]:
    """递归查找目录下所有 .xml 文件（跳过以 _ 开头的目录和文件）。"""
    xml_files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 跳过以 _ 开头的目录
        dirnames[:] = [d for d in dirnames if not d.startswith("_")]
        for fname in sorted(filenames):
            # 跳过以 _ 开头的文件
            if fname.startswith("_"):
                continue
            if fname.lower().endswith(".xml"):
                xml_files.append(os.path.join(dirpath, fname))
    return xml_files


def main():
    # 确定扫描目录或单个文件
    if len(sys.argv) > 1:
        target = os.path.abspath(sys.argv[1])
    else:
        target = os.getcwd()

    if os.path.isfile(target):
        if not target.lower().endswith(".xml"):
            print(f"指定的文件不是 .xml 文件: {target}")
            return
        root_dir = os.path.dirname(target)
        xml_files = [target]
        print(f"检查文件: {target}\n")
    else:
        root_dir = target
        print(f"扫描目录: {root_dir}\n")
        xml_files = find_xml_files(root_dir)
        if not xml_files:
            print("未找到任何 .xml 文件。")
            return

    # ─── 格式检查 ─────────────────────────────────────────────────────────
    print("=" * 60)
    print(" XML 格式检查")
    print("=" * 60)

    passed = 0
    failed = 0
    failed_files = []

    for filepath in xml_files:
        relpath = os.path.relpath(filepath, root_dir)
        ok, msg = check_xml_wellformed(filepath)
        if ok:
            print(f"  ✓ {relpath}")
            passed += 1
        else:
            print(f"  ✗ {relpath}")
            print(f"    └─ {msg}")
            failed += 1
            failed_files.append((relpath, msg))

    print()
    print(f"结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 个文件")
    print()

    # ─── 字数统计 ─────────────────────────────────────────────────────────
    print(f"  {'文件':<38} {'中文':>4} {'英文':>4} {'总计':>4}")
    print(f"  {'-' * 40} {'-' * 6} {'-' * 6} {'-' * 6}")

    total_chinese = 0
    total_english = 0
    total_all = 0

    for filepath in xml_files:
        relpath = os.path.relpath(filepath, root_dir)
        text = extract_text(filepath)
        counts = count_words(text)

        total_chinese += counts["chinese"]
        total_english += counts["english"]
        total_all += counts["total"]

        # 截断过长的路径用于对齐显示
        display_path = relpath if len(relpath) <= 40 else "..." + relpath[-37:]
        print(
            f"  {display_path:<40} {counts['chinese']:>6} "
            f"{counts['english']:>6} {counts['total']:>6}"
        )

    print(f"  {'-' * 40} {'-' * 6} {'-' * 6} {'-' * 6}")
    print(f"  {'合计':<38} {total_chinese:>6} {total_english:>6} {total_all:>6}")
    print()

    # ─── 汇总 ─────────────────────────────────────────────────────────────
    if failed_files:
        print("=" * 60)
        print(" 格式错误汇总")
        print("=" * 60)
        for relpath, msg in failed_files:
            print(f"  {relpath}: {msg}")
        print()
        exit(1)


if __name__ == "__main__":
    main()
