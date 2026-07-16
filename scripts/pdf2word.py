#!/usr/bin/env python3
"""
PDF转Word工具.

用法:
    python scripts/pdf2word.py input.pdf
    python scripts/pdf2word.py input.pdf -o output.docx
    python scripts/pdf2word.py input.pdf --pages 1-5
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from lib.exceptions import (
    ConversionError,
    DependencyError,
    InputFileNotFoundError,
    InvalidInputError,
    ScriptError,
)

PRESETS: dict[str, dict[str, bool | float]] = {
    "default": {
        "multi_processing": True,
    },
    "contract": {
        "multi_processing": False,
        "parse_lattice_table": True,
        "parse_stream_table": True,
        "max_border_width": 3.0,
        "connected_border_tolerance": 0.3,
        "line_separate_threshold": 3.0,
        "min_border_clearance": 1.0,
    },
    "table": {
        "multi_processing": True,
        "parse_lattice_table": True,
        "parse_stream_table": True,
        "float_image_ignorable_gap": 2.0,
        "extract_stream_table": True,
    },
    "text": {
        "multi_processing": True,
        "parse_lattice_table": False,
        "parse_stream_table": False,
        "new_paragraph_free_space_ratio": 0.7,
    },
}


def parse_args():
    """解析命令行参数."""
    parser = argparse.ArgumentParser(
        description="PDF转Word工具 - 将PDF文件转换为可编辑的Word文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s document.pdf
  %(prog)s document.pdf -o result.docx
  %(prog)s document.pdf --pages 1-5
  %(prog)s document.pdf --pages 1,3,5-10
  %(prog)s document.pdf --preset contract
  %(prog)s document.pdf -o result.docx --force
        """,
    )

    parser.add_argument("input", help="输入PDF文件路径")
    parser.add_argument("-o", "--output", help="输出Word文件路径 (默认: 输入文件名.docx)")
    parser.add_argument("--pages", help="页码范围 (如: 1-5, 1,3,5-10)")
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="default",
        help="预设模式: default(默认), contract(合同), table(表格), text(纯文本)",
    )
    parser.add_argument("--debug", action="store_true", help="输出调试信息")
    parser.add_argument("-f", "--force", action="store_true", help="强制覆盖已存在的输出文件")

    return parser.parse_args()


def validate_input(input_path: str) -> Path:
    """
    验证输入文件.

    Args:
        input_path: 输入文件路径

    Returns:
        Path: 验证后的文件路径

    Raises:
        InputFileNotFoundError: 文件不存在
        InvalidInputError: 文件格式错误
    """
    path = Path(input_path)

    if not path.exists():
        raise InputFileNotFoundError(f"文件不存在: {input_path}")

    if path.suffix.lower() != ".pdf":
        raise InvalidInputError(f"文件格式错误: 需要PDF文件，当前为 {path.suffix}")

    return path


def parse_page_range(page_str: str) -> list[int] | None:
    """
    解析页码范围字符串.

    支持格式:
        1-5      -> [1, 2, 3, 4, 5]
        1,3,5    -> [1, 3, 5]
        1-3,5,7-9 -> [1, 2, 3, 5, 7, 8, 9]

    Args:
        page_str: 页码范围字符串

    Returns:
        排序后的页码列表，None表示全部页面

    Raises:
        InvalidInputError: 页码范围无效
    """
    if not page_str:
        return None

    pages: set[int] = set()
    parts = page_str.split(",")

    for raw_part in parts:
        part = raw_part.strip()
        if "-" in part:
            try:
                start_str, end_str = part.split("-")
                start = int(start_str.strip())
                end = int(end_str.strip())
                if start < 1 or end < 1:
                    raise InvalidInputError(f"页码必须为正整数: {page_str}")
                if start > end:
                    raise InvalidInputError(
                        f"页码范围无效: {page_str} (起始页 {start} 大于结束页 {end})"
                    )
                pages.update(range(start, end + 1))
            except ValueError:
                raise InvalidInputError(f"页码范围无效: {page_str}")
        else:
            try:
                page_num = int(part)
                if page_num < 1:
                    raise InvalidInputError(f"页码必须为正整数: {page_str}")
                pages.add(page_num)
            except ValueError:
                raise InvalidInputError(f"页码范围无效: {page_str}")

    return sorted(pages)


def convert_pdf_to_docx(
    input_path: Path,
    output_path: Path,
    pages: list[int] | None = None,
    preset: str = "default",
    debug: bool = False,
) -> bool:
    """
    将PDF转换为Word文档.

    Args:
        input_path: 输入PDF文件路径
        output_path: 输出Word文件路径
        pages: 页码列表，None表示全部页面
        preset: 预设模式名称
        debug: 是否输出调试信息

    Returns:
        True if successful, False otherwise

    Raises:
        DependencyError: pdf2docx 未安装
        ConversionError: 转换过程出错
    """
    try:
        from pdf2docx import Converter
    except ImportError:
        raise DependencyError("pdf2docx 未安装，请运行: pip install pdf2docx")

    convert_params: dict = PRESETS.get(preset, PRESETS["default"]).copy()
    convert_params["debug"] = debug

    cv = None
    try:
        cv = Converter(str(input_path))
        if pages:
            cv.convert(str(output_path), pages=pages, **convert_params)
        else:
            cv.convert(str(output_path), **convert_params)
        return True
    except Exception as e:
        raise ConversionError(f"转换失败: {e}")
    finally:
        if cv:
            cv.close()


def main():
    """Entry point for the PDF-to-Word converter."""
    args = parse_args()

    try:
        input_path = validate_input(args.input)
        pages = parse_page_range(args.pages)
    except ScriptError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".docx")

    if output_path.exists() and not args.force:
        print(f"错误: 输出文件已存在: {output_path}", file=sys.stderr)
        print("提示: 使用 --force 参数强制覆盖", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    preset_str = f"预设: {args.preset}" if args.preset != "default" else ""
    print(f"正在转换: {input_path} -> {output_path} {preset_str}")

    try:
        convert_pdf_to_docx(input_path, output_path, pages, args.preset, args.debug)
        print(f"转换完成: {output_path}")
    except ScriptError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
