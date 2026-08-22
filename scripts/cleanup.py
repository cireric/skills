#!/usr/bin/env python3
"""
清理项目无用文件（跨平台，Windows/Linux/macOS 通用）.

- 清除 Python 缓存 (__pycache__, *.pyc, *.pyo, *.egg-info)
- 清除测试缓存 (.pytest_cache, .coverage, htmlcov)
- 清除工具缓存 (.playwright-mcp, .ipynb_checkpoints, .research_tmp)
- 清除临时文件 (*.tmp, *.temp, ~$*.xlsx)
- 清除输出报表 (output/ 目录，--keep-days 可保留最近N天，--keep-output 可整体跳过)
"""

import os
import shutil
import stat
import sys
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# rglob 扫描时跳过的目录（按路径分量精确匹配，避免误删 .venv 内文件/误入 .git）
SKIP_DIR_PARTS = {".git", ".venv", ".opencode", ".omo"}


def _force_write(path: str) -> None:
    """清除只读属性（Windows 下删除只读文件/目录必需）."""
    os.chmod(path, stat.S_IWRITE)


def _rmtree_onexc(func, target: str, _exc) -> None:
    """shutil.rmtree 回调：清除只读属性后重试删除."""
    _force_write(target)
    func(target)


def _delete_item(item: Path, dry_run: bool) -> tuple:
    """
    删除单个文件或目录.

    Args:
        item: 文件或目录路径
        dry_run: 是否仅预览

    Returns:
        (是否成功, 错误消息或None)
    """
    if dry_run:
        return True, None
    if not item.exists():
        # 已被同批次其他模式删除（如 __pycache__ 目录先删，内部 *.pyc 后到）
        return True, None
    try:
        if item.is_dir():
            shutil.rmtree(item, onexc=_rmtree_onexc)
        else:
            item.unlink()
        return True, None
    except PermissionError:
        # Windows 只读：清除属性后重试一次
        try:
            _force_write(item)
            if item.is_dir():
                shutil.rmtree(item, onexc=_rmtree_onexc)
            else:
                item.unlink()
            return True, None
        except Exception as e:
            return False, f"权限不足: {item} ({e})"
    except Exception as e:
        return False, f"删除失败: {item} ({e})"


def _should_keep_output_dir(dir_name: str, keep_recent_days: int) -> bool:
    """
    判断输出目录是否应该保留.

    Args:
        dir_name: 目录名（格式：YYYYMMDD）
        keep_recent_days: 保留天数

    Returns:
        是否保留
    """
    if keep_recent_days <= 0:
        return False

    try:
        dir_date = datetime.strptime(dir_name, "%Y%m%d")
        cutoff_date = datetime.now() - timedelta(days=keep_recent_days)
        return dir_date >= cutoff_date
    except ValueError:
        return False


GLOB_PATTERNS = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".ruff_cache",
    "*.tmp",
    "*.temp",
    "~$*.xlsx",
]

EXACT_PATHS = [
    ".pytest_cache",
    ".coverage",
    "htmlcov",
    ".playwright-mcp",
    ".research_tmp",
]


def _is_excluded(item: Path) -> bool:
    """路径中含受保护目录（.git/.venv）时跳过."""
    return any(part in SKIP_DIR_PARTS for part in item.parts)


def _collect_deletions(
    project_root: Path,
    dry_run: bool,
    keep_recent_days: int,
    clean_output: bool = True,
) -> tuple[list[str], list[str], list[str]]:
    """Scan project and collect items to delete, keep, and skip."""
    deleted: list[str] = []
    kept: list[str] = []
    skipped: list[str] = []

    for pattern in GLOB_PATTERNS:
        for item in project_root.rglob(pattern):
            if _is_excluded(item):
                continue
            success, error = _delete_item(item, dry_run)
            if success:
                deleted.append(str(item))
            elif error:
                skipped.append(error)

    for name in EXACT_PATHS:
        exact_item = project_root / name
        if exact_item.exists():
            success, error = _delete_item(exact_item, dry_run)
            if success:
                deleted.append(str(exact_item))
            elif error:
                skipped.append(error)

    if not clean_output:
        return deleted, kept, skipped

    output_dir = project_root / "output"
    if output_dir.exists():
        for dir_item in output_dir.iterdir():
            if dir_item.is_dir() and _should_keep_output_dir(dir_item.name, keep_recent_days):
                kept.append(str(dir_item))
                continue

            success, error = _delete_item(dir_item, dry_run)
            if success:
                deleted.append(str(dir_item))
            elif error:
                skipped.append(error)

    return deleted, kept, skipped


def _print_results(deleted: list[str], kept: list[str], skipped: list[str], dry_run: bool) -> None:
    """Print cleanup results summary."""
    print(f"\n已删除 ({len(deleted)} 项):")
    for del_item in deleted:
        print(f"  - {del_item}")

    if kept:
        print(f"\n已保留 ({len(kept)} 项):")
        for kept_item in kept:
            print(f"  - {kept_item}")

    if skipped:
        print(f"\n已跳过 ({len(skipped)} 项):")
        for skip_item in skipped:
            print(f"  - {skip_item}")

    print(f"\n{'预览完成，未实际删除' if dry_run else '清理完成'}")


def clean_project(
    keep_recent_days: int = 0, dry_run: bool = False, keep_output: bool = False
):
    """
    清理项目无用文件.

    Args:
        keep_recent_days: 保留最近N天的报表 (0=全部删除)
        dry_run: 仅显示将删除的文件，不实际删除
        keep_output: 完全不清理 output/ 目录
    """
    project_root = Path(__file__).parent.parent

    print(f"项目根目录: {project_root}")
    if keep_output:
        print("输出报表: 保留 (不清理 output/)")
    else:
        print(f"输出报表: 保留最近 {keep_recent_days} 天")
    print(f"模式: {'预览' if dry_run else '执行删除'}")
    print("-" * 50)

    deleted, kept, skipped = _collect_deletions(
        project_root, dry_run, keep_recent_days, clean_output=not keep_output
    )
    _print_results(deleted, kept, skipped, dry_run)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理项目无用文件（跨平台）")
    parser.add_argument(
        "--keep-days",
        type=int,
        default=0,
        help="保留最近N天的报表 (默认: 0=全部删除)",
    )
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="完全不清理 output/ 目录",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际删除",
    )

    args = parser.parse_args()
    clean_project(
        keep_recent_days=args.keep_days, dry_run=args.dry_run, keep_output=args.keep_output
    )
