"""Validate docstrings for every Python function in a source tree."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
}


def _python_files(root: Path) -> list[Path]:
    """Collect Python files while skipping generated and dependency folders.

    Args:
        root: Source file or directory to inspect.

    Returns:
        Sorted Python files below ``root``.
    """
    if root.is_file():
        return [root]
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in EXCLUDED_DIRECTORIES for part in path.parts)
    )


def _has_section(docstring: str, section: str) -> bool:
    """Check whether a Google-style documentation section exists.

    Args:
        docstring: Function docstring to inspect.
        section: Section name such as ``Args`` or ``Returns``.

    Returns:
        ``True`` when the requested section heading is present.
    """
    return bool(re.search(rf"^\s*{re.escape(section)}:\s*$", docstring, re.MULTILINE))


def _requires_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Determine whether a function has arguments worth documenting.

    Args:
        node: Parsed function definition.

    Returns:
        ``True`` when the function has arguments other than an implicit
        ``self`` or ``cls`` receiver.
    """
    positional = [*node.args.posonlyargs, *node.args.args]
    if positional and positional[0].arg in {"self", "cls"}:
        positional = positional[1:]
    return bool(
        positional or node.args.vararg or node.args.kwonlyargs or node.args.kwarg
    )


def check_file(path: Path) -> list[str]:
    """Find missing or incomplete function docstrings in one Python file.

    Args:
        path: Python file to parse and validate.

    Returns:
        Human-readable validation errors, empty when the file passes.
    """
    try:
        tree = ast.parse(path.read_text(), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: cannot parse file: {exc}"]

    errors: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node, clean=False)
        location = f"{path}:{node.lineno} ({node.name})"
        if not docstring:
            errors.append(f"{location}: missing docstring")
            continue
        if _requires_args(node) and not _has_section(docstring, "Args"):
            errors.append(f"{location}: missing Args section")
        if not _has_section(docstring, "Returns") and not _has_section(
            docstring, "Yields"
        ):
            errors.append(f"{location}: missing Returns or Yields section")
    return errors


def main(argv: list[str] | None = None) -> int:
    """Run the repository-wide Python docstring validation command.

    Args:
        argv: Optional command-line arguments without the executable name.

    Returns:
        Zero when all functions pass, otherwise one.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", type=Path, help="Python file or source directory to inspect"
    )
    args = parser.parse_args(argv)

    errors = [error for path in _python_files(args.root) for error in check_file(path)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Docstring check passed for {len(_python_files(args.root))} Python files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
