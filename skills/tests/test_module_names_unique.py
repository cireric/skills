"""Guard: skill 顶层模块名必须在全局测试命名空间内唯一。

全局跑 pytest（`testpaths = skills scripts`）时，所有 skill 的 conftest/test 在
同一个进程里共享 sys.path 与 sys.modules：若两个 skill 暴露同名顶层模块
（例如各自有一个 `cli.py`），先被 import 者会缓存在 sys.modules 中，后者的
`import cli` 拿到的是前者的实现——测试静默测错对象，且结果依赖 conftest
加载顺序（先加载谁谁赢）。

本测试静态扫描每个 skill 的顶层可导入名（根目录直接 .py 文件 + 含
`__init__.py` 的包，含约定俗成的 `scripts/` 子目录），并叠加仓库根层的
顶层名（如根 `scripts/` namespace 包），断言全局无重复，把此类冲突从
"运行时才暴露"前移到"收集即失败"。

例外：`cli.py` 入口薄壳只按路径执行（`python skills/<skill>/cli.py`），
从不被测试 import，不参与命名空间，见 `ENTRY_SHIM_NAMES`。
"""
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]

# 例外：只按路径执行、禁止被测试 import 的入口薄壳名
ENTRY_SHIM_NAMES = {"cli"}


def _importable_names(root: Path) -> dict[str, Path]:
    """Return {module_name: path} of importables directly under `root`."""
    names: dict[str, Path] = {}
    for p in sorted(root.iterdir()):
        if p.name.startswith(".") or p.name == "__pycache__":
            continue
        if p.is_file() and p.suffix == ".py" and p.name != "__init__.py":
            names[p.stem] = p
        elif p.is_dir() and (p / "__init__.py").is_file():
            names[p.name] = p
    return names


def _scan_skill(skill_dir: Path) -> dict[str, Path]:
    """Top-level importable names of one skill (root + conventional scripts/)."""
    roots = [skill_dir]
    scripts = skill_dir / "scripts"
    if scripts.is_dir():
        roots.append(scripts)
    out: dict[str, Path] = {}
    for root in roots:
        for name, path in _importable_names(root).items():
            out.setdefault(name, path)
    return out


def _repo_root_importables(root: Path) -> dict[str, Path]:
    """仓库根层可导入名：直接 .py 文件 + 含 `__init__.py` 或直接含 .py 文件的目录.

    后者是 namespace 包（如根 `scripts/`），同样占据顶层名字。
    """
    names: dict[str, Path] = {}
    for p in sorted(root.iterdir()):
        if p.name.startswith(".") or p.name == "__pycache__":
            continue
        if p.is_file() and p.suffix == ".py":
            names[p.stem] = p
        elif p.is_dir():
            has_direct_py = any(q.suffix == ".py" for q in p.iterdir())
            if (p / "__init__.py").is_file() or has_direct_py:
                names[p.name] = p
    return names


def test_skill_top_level_module_names_are_unique():
    seen: dict[str, list[Path]] = {}
    for name, path in _repo_root_importables(REPO_ROOT).items():
        seen.setdefault(name, []).append(path)
    for skill_dir in sorted(SKILLS_ROOT.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        if skill_dir.name == "tests":
            continue  # 本守卫测试自身，不属于任何 skill
        for name, path in _scan_skill(skill_dir).items():
            if name in ENTRY_SHIM_NAMES:
                continue
            seen.setdefault(name, []).append(path)

    dupes = {name: paths for name, paths in seen.items() if len(paths) > 1}
    assert not dupes, (
        "全局测试命名冲突：以下顶层模块名被多个 skill 暴露，"
        "先 import 者会遮蔽后者（sys.modules 缓存）：\n"
        + "\n".join(
            f"  {name}: " + ", ".join(str(p) for p in paths)
            for name, paths in sorted(dupes.items())
        )
    )
