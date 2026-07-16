#!/usr/bin/env python3
"""
Markdown转PDF工具.

用法:
    单文件转换:
    python scripts/md2pdf.py input.md
    python scripts/md2pdf.py input.md -o output.pdf
    python scripts/md2pdf.py input.md --pdf-engine xelatex
    python scripts/md2pdf.py input.md --toc --force

    批量转换:
    python scripts/md2pdf.py --batch folder/
    python scripts/md2pdf.py --batch folder/ --output output/
    python scripts/md2pdf.py --batch folder/ --recursive --force
"""

import argparse
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))
from lib.converter_base import (
    detect_chinese,
    find_pandoc,
    get_available_pdf_engines,
    get_chinese_font,
    parse_frontmatter,
    resolve_output,
    validate_input,
)
from lib.exceptions import (
    ConversionError,
    DependencyError,
    ScriptError,
)


def parse_args(args=None):
    """Parse command-line arguments for the PDF converter."""
    parser = argparse.ArgumentParser(
        description="Markdown转PDF工具 - 将Markdown文件转换为PDF文档",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  单文件转换:
  %(prog)s document.md
  %(prog)s document.md -o result.pdf
  %(prog)s document.md --pdf-engine xelatex
  %(prog)s document.md --toc
  %(prog)s document.md -o result.pdf --force

  批量转换:
  %(prog)s --batch folder/
  %(prog)s --batch folder/ --output output/
  %(prog)s --batch folder/ --recursive --force
        """,
    )

    parser.add_argument("--version", action="version", version="md2pdf 1.0")

    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("input", nargs="?", help="输入Markdown文件路径")
    input_group.add_argument("--batch", metavar="DIR", help="批量转换模式：指定文件夹路径")

    parser.add_argument("-o", "--output", help="输出PDF文件路径 (单文件) 或输出目录 (批量模式)")
    parser.add_argument(
        "--pdf-engine",
        help="PDF引擎 (weasyprint/xelatex/wkhtmltopdf/pdflatex)",
    )
    parser.add_argument("--toc", action="store_true", help="生成目录")
    parser.add_argument("--debug", action="store_true", help="输出调试信息")
    parser.add_argument("-f", "--force", action="store_true", help="强制覆盖已存在的输出文件")
    parser.add_argument(
        "-r", "--recursive", action="store_true", help="递归处理子文件夹 (批量模式)"
    )

    return parser.parse_args(args)


def generate_install_guide() -> str:
    """Return a guide for installing PDF engines when none is found."""
    return """错误: 未找到可用的 PDF 引擎

请安装以下任一引擎：

1. WeasyPrint (推荐，纯 Python):
   - 运行: pip install weasyprint

2. XeLaTeX (推荐中文文档):
   - Windows: 下载 MiKTeX https://miktex.org/download
   - 或运行: winget install MiKTeX.MiKTeX

3. wkhtmltopdf:
   - Windows: https://wkhtmltopdf.org/downloads.html
   - 或运行: winget install wkhtmltopdf

4. pdfLaTeX:
   - Windows: 下载 MiKTeX https://miktex.org/download
"""


def select_pdf_engine(content: str, user_engine: str | None = None, debug: bool = False) -> str:
    """Select the best PDF engine based on content and availability."""
    if user_engine:
        if debug:
            print(f"使用用户指定的PDF引擎: {user_engine}")
        return str(user_engine)

    available_engines = get_available_pdf_engines()

    if not available_engines:
        raise DependencyError(generate_install_guide())

    if detect_chinese(content):
        for engine in ["xelatex", "weasyprint"]:
            if engine in available_engines:
                if debug:
                    print(f"检测到中文内容，使用引擎: {engine}")
                return engine

    selected = str(available_engines[0])
    if debug:
        print(f"自动选择PDF引擎: {selected}")
    return selected


def _preprocess_content(content: str) -> str:
    """Remove image alt text and format author/time/source metadata lines."""
    processed_content = re.sub(r"!\[[^\]]*\]", "![]", content)

    lines = processed_content.split("\n")
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("**作者：**"):
            author = line.replace("**作者：**", "").strip()
            new_lines.append(f"**作者：** {author}  ")
            i += 1
        elif line.startswith("**发布时间：**"):
            time = line.replace("**发布时间：**", "").strip()
            new_lines.append(f"**发布时间：** {time}  ")
            i += 1
        elif line.startswith("**来源：**"):
            url = line.replace("**来源：**", "").strip()
            new_lines.append(f"**来源：** [{url}]({url})")
            i += 1
        else:
            new_lines.append(lines[i])
            i += 1

    return "\n".join(new_lines)


def _build_conversion_args(
    processed_content: str,
    selected_engine: str,
    output_path: Path,
    frontmatter: dict,
    toc: bool,
    debug: bool,
) -> tuple[list[str], Path | None]:
    """Build pypandoc extra_args with engine, CSS, font, TOC, and frontmatter settings."""
    extra_args = ["--pdf-engine", selected_engine]

    css_file = None
    if selected_engine == "wkhtmltopdf":
        css_content = """
@page { margin: 0; }
body { background-color: white; margin: 0; padding: 0; }
h1 { margin-top: 0; margin-bottom: 0.3em; }
img { max-width: 480px; max-height: 600px; display: block; margin: 1em auto; object-fit: contain; }
figure { margin: 1em 0; text-align: center; }
p, h1, h2, h3, h4, h5, h6 { margin: 0.3em 0; }
a { color: #0066cc; text-decoration: none; }
"""
        css_file = output_path.with_suffix(".temp.css")
        css_file.write_text(css_content, encoding="utf-8")
        extra_args.extend(["--css", str(css_file)])
        extra_args.extend(
            [
                "--pdf-engine-opt=--margin-top",
                "--pdf-engine-opt=5mm",
                "--pdf-engine-opt=--margin-bottom",
                "--pdf-engine-opt=10mm",
                "--pdf-engine-opt=--margin-left",
                "--pdf-engine-opt=15mm",
                "--pdf-engine-opt=--margin-right",
                "--pdf-engine-opt=15mm",
            ]
        )

    if detect_chinese(processed_content):
        font = get_chinese_font()
        if font:
            extra_args.extend(["--variable", f"mainfont:{font}"])
            if debug:
                print(f"使用中文字体: {font}")

    if toc:
        extra_args.append("--toc")

    if "title" in frontmatter:
        extra_args.extend(["--metadata", f"title={frontmatter['title']}"])
    if "author" in frontmatter:
        extra_args.extend(["--metadata", f"author={frontmatter['author']}"])

    if debug:
        print(f"  extra_args={extra_args}")

    return extra_args, css_file


def convert_md_to_pdf(
    input_path: Path,
    output_path: Path,
    pdf_engine: str | None = None,
    toc: bool = False,
    debug: bool = False,
) -> bool:
    """Convert a Markdown file to PDF using pypandoc."""
    try:
        import pypandoc
    except ImportError:
        raise DependencyError("pypandoc 未安装，请运行: pip install pypandoc")

    pandoc_path = find_pandoc()
    if pandoc_path:
        os.environ["PATH"] = os.path.dirname(pandoc_path) + os.pathsep + os.environ.get("PATH", "")
        if debug:
            print(f"找到 pandoc: {pandoc_path}")

    content = input_path.read_text(encoding="utf-8")
    processed_content = _preprocess_content(content)

    selected_engine = select_pdf_engine(processed_content, pdf_engine, debug)
    frontmatter = parse_frontmatter(content)

    extra_args, css_file = _build_conversion_args(
        processed_content, selected_engine, output_path, frontmatter, toc, debug
    )

    if debug:
        print(f"转换参数: input={input_path}, output={output_path}")

    temp_md = output_path.with_suffix(".temp.md")

    try:
        temp_md.write_text(processed_content, encoding="utf-8")
        pypandoc.convert_file(
            str(temp_md), "pdf", outputfile=str(output_path), extra_args=extra_args
        )
        return True
    except Exception as e:
        raise ConversionError(f"转换失败: {e}")
    finally:
        if temp_md.exists():
            temp_md.unlink()
        if css_file and css_file.exists():
            css_file.unlink()


def find_md_files(directory: Path, recursive: bool = False) -> list:
    """查找目录下的所有Markdown文件."""
    md_files = []
    pattern = "**/*.md" if recursive else "*.md"

    for md_file in directory.glob(pattern):
        if md_file.is_file() and md_file.suffix.lower() in (".md", ".markdown"):
            md_files.append(md_file)

    return sorted(md_files)


def batch_convert(
    input_dir: Path,
    output_dir: Path | None,
    pdf_engine: str | None,
    toc: bool,
    debug: bool,
    force: bool,
    recursive: bool,
) -> tuple:
    """批量转换文件夹下的Markdown文件."""
    if not input_dir.is_dir():
        print(f"错误: '{input_dir}' 不是有效的目录", file=sys.stderr)
        return 0, 0

    md_files = find_md_files(input_dir, recursive)

    if not md_files:
        print(f"警告: 在 '{input_dir}' 中未找到Markdown文件")
        return 0, 0

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    fail_count = 0

    for i, md_file in enumerate(md_files, 1):
        relative_path = md_file.relative_to(input_dir)

        if output_dir:
            if recursive and relative_path.parent != Path("."):
                out_dir = output_dir / relative_path.parent
                out_dir.mkdir(parents=True, exist_ok=True)
            else:
                out_dir = output_dir
        else:
            out_dir = md_file.parent

        output_path = out_dir / (md_file.stem + ".pdf")

        print(f"[{i}/{len(md_files)}] 正在转换: {relative_path}")

        try:
            convert_md_to_pdf(md_file, output_path, pdf_engine, toc, debug)
            print(f"  ✓ 完成: {output_path}")
            success_count += 1
        except ScriptError as e:
            print(f"  ✗ 失败: {e}", file=sys.stderr)
            fail_count += 1
        except Exception as e:
            print(f"  ✗ 异常: {e}", file=sys.stderr)
            fail_count += 1

    return success_count, fail_count


def main():
    """Entry point for the Markdown-to-PDF converter."""
    args = parse_args()

    if args.batch:
        input_dir = Path(args.batch)
        output_dir = Path(args.output) if args.output else None

        print(f"批量转换模式: {input_dir}")
        if args.recursive:
            print("  - 递归处理子文件夹")
        if output_dir:
            print(f"  - 输出目录: {output_dir}")

        success, fail = batch_convert(
            input_dir,
            output_dir,
            args.pdf_engine,
            args.toc,
            args.debug,
            args.force,
            args.recursive,
        )

        print(f"\n转换完成: 成功 {success} 个, 失败 {fail} 个")
        sys.exit(0 if fail == 0 else 1)

    if not args.input:
        print("错误: 请指定输入文件或使用 --batch 模式", file=sys.stderr)
        sys.exit(1)

    try:
        input_path = validate_input(args.input, (".md", ".markdown"))
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        output_path = resolve_output(input_path, args.output, args.force, ".pdf")
    except FileExistsError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"正在转换: {input_path} -> {output_path}")

    try:
        convert_md_to_pdf(input_path, output_path, args.pdf_engine, args.toc, args.debug)
        print(f"转换完成: {output_path}")
    except ScriptError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
