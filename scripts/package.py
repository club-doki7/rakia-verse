#!/usr/bin/env python3
"""
XML 打包脚本
用于 rakia-verse 项目，将整个仓库打包为单个 XML 文件。
脚本会递归解析所有 XInclude 引用，生成一个包含全部内容的独立 XML 文件。

用法:
    python _scripts/package.py [output_file]
    [output_file] 为输出文件名。若省略，默认为 "rakia-verse-package.xml"。

输出:
    一个包含所有内容的单一 XML 文件，所有 xi:include 引用均已内联展开。
"""

import os
import sys
from xml.etree import ElementTree as ET

# 强制标准输出和标准错误使用 UTF-8 编码
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# XInclude 命名空间
XI_NS = "http://www.w3.org/2001/XInclude"
XI_INCLUDE_TAG = f"{{{XI_NS}}}include"

# 注册命名空间前缀，避免输出时变为 ns0、ns1 等
ET.register_namespace("xi", XI_NS)


def parse_xml(filepath: str) -> ET.ElementTree:
    """解析 XML 文件，保留注释节点。"""
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    return ET.parse(filepath, parser)


def resolve_xincludes(element: ET.Element, base_dir: str, visited: set[str] | None = None) -> ET.Element:
    """
    递归解析 element 中的所有 xi:include 元素，将其替换为被引用文件的根元素内容。

    参数:
        element: 当前待处理的 XML 元素
        base_dir: 当前文件所在目录（用于解析相对路径）
        visited: 已访问文件集合（用于检测循环引用）

    返回:
        处理完毕的元素（原地修改）
    """
    if visited is None:
        visited = set()

    # 收集需要替换的 xi:include 元素
    # 不能在迭代过程中修改子元素列表，所以先收集再替换
    includes_to_resolve = []
    for i, child in enumerate(element):
        if child.tag == XI_INCLUDE_TAG:
            includes_to_resolve.append((i, child))
        else:
            # 递归处理非 xi:include 的子元素
            resolve_xincludes(child, base_dir, visited)

    # 从后向前替换，避免索引偏移
    for i, include_elem in reversed(includes_to_resolve):
        href = include_elem.get("href")
        if href is None:
            print(f"  警告: 发现缺少 href 属性的 xi:include 元素，已跳过")
            continue

        # 解析文件路径
        include_path = os.path.normpath(os.path.join(base_dir, href))

        if not os.path.isfile(include_path):
            print(f"  警告: 引用文件不存在: {include_path}，已跳过")
            continue

        # 检测循环引用
        abs_path = os.path.abspath(include_path)
        if abs_path in visited:
            print(f"  警告: 检测到循环引用: {include_path}，已跳过")
            continue

        # 获取 comment 属性（如果有的话，作为注释保留）
        comment = include_elem.get("comment")

        # 解析被引用的文件
        try:
            included_tree = parse_xml(include_path)
            included_root = included_tree.getroot()
        except ET.ParseError as e:
            print(f"  错误: 解析文件失败 {include_path}: {e}")
            continue
        except Exception as e:
            print(f"  错误: 读取文件失败 {include_path}: {e}")
            continue

        # 递归解析被引用文件中的 xi:include
        new_visited = visited | {abs_path}
        included_dir = os.path.dirname(include_path)
        resolve_xincludes(included_root, included_dir, new_visited)

        # 移除被引用根元素上的 xmlns:xi 声明（已经不再需要）
        # ElementTree 不直接暴露命名空间声明，但注册的前缀会在序列化时自动处理

        # 用被引用文件的根元素替换 xi:include 元素
        element.remove(include_elem)
        element.insert(i, included_root)

        # 如果有 comment 属性，将其作为处理日志输出
        if comment:
            print(f"  已内联: {href} ({comment})")
        else:
            print(f"  已内联: {href}")

    return element


def clean_xi_namespace(element: ET.Element):
    """
    递归清除元素及其子元素上残留的 xmlns:xi 命名空间声明相关属性。
    同时移除所有 xi:include 的 comment 属性（如果存在于已解析的元素上）。
    """
    # 跳过注释节点
    if callable(element.tag):
        return

    # 移除属性中的 xi 命名空间相关项
    attrs_to_remove = [
        key for key in element.attrib
        if key.startswith(f"{{{XI_NS}}}") or key == f"xmlns:xi"
    ]
    for key in attrs_to_remove:
        del element.attrib[key]

    for child in element:
        clean_xi_namespace(child)


def _serialize_element(element: ET.Element, level: int, indent_str: str) -> list[str]:
    """
    递归将元素序列化为格式化的字符串行列表。
    对含多行文本内容的元素，按当前层级重新缩进文本。
    支持注释节点的序列化。
    """
    indent = indent_str * level
    child_indent = indent_str * (level + 1)
    lines = []

    # 处理注释节点
    if callable(element.tag):
        # ET.Comment 的 tag 是一个函数对象
        comment_text = element.text or ""
        if "\n" in comment_text:
            # 多行注释
            comment_lines = _reindent_text(comment_text, level + 1, indent_str)
            lines.append(f"{indent}<!--")
            lines.extend(comment_lines)
            lines.append(f"{indent}-->")
        else:
            lines.append(f"{indent}<!--{comment_text}-->")
        return lines

    # 构建开始标签
    tag = element.tag
    attrs = ""
    for key, value in element.attrib.items():
        # 转义属性值中的特殊字符
        value = value.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")
        attrs += f' {key}="{value}"'

    has_children = len(element) > 0
    text = element.text or ""
    text_stripped = text.strip()

    if not has_children and not text_stripped:
        # 空元素
        lines.append(f"{indent}<{tag}{attrs} />")
    elif not has_children and text_stripped:
        # 叶子元素，有文本内容
        if "\n" in text_stripped:
            # 多行文本：重新缩进
            text_lines = _reindent_text(text, level + 1, indent_str)
            lines.append(f"{indent}<{tag}{attrs}>")
            lines.extend(text_lines)
            lines.append(f"{indent}</{tag}>")
        else:
            # 单行文本：内联
            escaped = text_stripped.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            lines.append(f"{indent}<{tag}{attrs}>{escaped}</{tag}>")
    else:
        # 有子元素
        lines.append(f"{indent}<{tag}{attrs}>")

        # 如果开始标签后有文本内容（混合内容，少见）
        if text_stripped:
            text_lines = _reindent_text(text, level + 1, indent_str)
            lines.extend(text_lines)

        # 递归处理子元素
        for child in element:
            lines.extend(_serialize_element(child, level + 1, indent_str))

            # 子元素的 tail 文本（子元素之后、下一个兄弟之前的文本）
            tail = child.tail or ""
            tail_stripped = tail.strip()
            if tail_stripped:
                tail_lines = _reindent_text(tail, level + 1, indent_str)
                lines.extend(tail_lines)

        lines.append(f"{indent}</{tag}>")

    return lines


def _reindent_text(text: str, level: int, indent_str: str) -> list[str]:
    """
    将多行文本按指定层级重新缩进。
    去除原有公共缩进，去除首尾空行，加上新的缩进。
    接收原始文本（未经 strip），自行处理。
    """
    text_lines = text.split("\n")

    # 去除首尾空行
    while text_lines and not text_lines[0].strip():
        text_lines.pop(0)
    while text_lines and not text_lines[-1].strip():
        text_lines.pop()

    if not text_lines:
        return []

    # 计算非空行的最小缩进（公共前缀）
    min_indent = float("inf")
    for line in text_lines:
        if line.strip():
            leading = len(line) - len(line.lstrip())
            min_indent = min(min_indent, leading)
    if min_indent == float("inf"):
        min_indent = 0

    # 去除公共缩进，加上新缩进
    new_indent = indent_str * level
    result = []
    for line in text_lines:
        if line.strip():
            result.append(f"{new_indent}{line[min_indent:]}")
        else:
            result.append("")
    return result


def indent_xml(element: ET.Element, indent_str: str = "  ") -> str:
    """
    将 XML 元素树序列化为格式化的字符串。
    自定义序列化，正确处理含多行文本内容的元素。
    """
    lines = _serialize_element(element, 0, indent_str)
    return "\n".join(lines)


def extract_metadata(readme_file: str) -> ET.Element | None:
    """
    从 readme.xml 中抽取 <metadata> 元素。

    参数:
        readme_file: readme.xml 文件路径

    返回:
        metadata 元素，若未找到则返回 None
    """
    try:
        tree = parse_xml(readme_file)
        root = tree.getroot()
    except (ET.ParseError, FileNotFoundError) as e:
        print(f"警告: 无法解析 readme.xml: {e}")
        return None

    metadata = root.find("metadata")
    if metadata is None:
        print("警告: readme.xml 中未找到 <metadata> 元素")
    return metadata


def package(entry_file: str, output_file: str):
    """
    主打包逻辑：从入口文件开始，解析所有 XInclude 引用，输出单个 XML 文件。

    参数:
        entry_file: 入口 XML 文件路径 (rakia-verse.xml)
        output_file: 输出文件路径
    """
    print(f"入口文件: {entry_file}")
    print(f"输出文件: {output_file}")
    print()

    # 解析入口文件
    try:
        tree = parse_xml(entry_file)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"错误: 入口文件解析失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"错误: 入口文件不存在: {entry_file}")
        sys.exit(1)

    # 记录入口文件为已访问
    base_dir = os.path.dirname(os.path.abspath(entry_file))
    visited = {os.path.abspath(entry_file)}

    print("正在解析 XInclude 引用...")
    resolve_xincludes(root, base_dir, visited)

    # 清理残留的 xi 命名空间引用
    clean_xi_namespace(root)

    # 从 readme.xml 抽取 metadata 并注入打包产物根元素
    readme_file = os.path.join(base_dir, "readme.xml")
    metadata = extract_metadata(readme_file)
    if metadata is not None:
        clean_xi_namespace(metadata)
        root.insert(0, metadata)
        print("已注入 metadata 元素")

    # 格式化输出
    formatted_xml = indent_xml(root)

    print()
    print("正在写入输出文件...")

    # 写入文件
    with open(output_file, "w", encoding="UTF-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(formatted_xml)
        f.write("\n")

    # 验证输出文件大小
    file_size = os.path.getsize(output_file)
    if file_size < 100:
        print(f"警告: 输出文件过小 ({file_size} bytes)，可能打包不完整")
    else:
        size_str = (
            f"{file_size / 1024:.1f} KB"
            if file_size < 1024 * 1024
            else f"{file_size / (1024 * 1024):.2f} MB"
        )
        print(f"完成! 输出文件大小: {size_str}")


def main():
    # 确定工作目录（脚本所在目录的上一级，即仓库根目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)

    # 切换到仓库根目录
    os.chdir(repo_root)

    # 确定输出文件名
    if len(sys.argv) > 1:
        output_file = sys.argv[1]
    else:
        output_file = "rakia-verse-package.xml"

    # 使用绝对路径
    output_file = os.path.abspath(output_file)

    # 入口文件
    entry_file = os.path.join(repo_root, "rakia-verse.xml")

    if not os.path.isfile(entry_file):
        print(f"错误: 找不到入口文件 {entry_file}")
        print("请确保在仓库根目录下运行此脚本，或从 _scripts 目录运行。")
        sys.exit(1)

    package(entry_file, output_file)


if __name__ == "__main__":
    main()
