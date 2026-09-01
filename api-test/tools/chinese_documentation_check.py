"""校验工作区的说明性文本是否使用简体中文。"""

from __future__ import annotations

import argparse
import ast
import io
import re
import tokenize
from pathlib import Path


排除目录 = {
    ".git",
    ".idea",
    ".venv",
    ".deepeval",
    ".pytest_cache",
    "__pycache__",
    "code_repo",
    "logs",
    "report",
    "runtime",
}
中文字符 = re.compile(r"[\u4e00-\u9fff]")
英文单词 = re.compile(r"[A-Za-z]{3,}")
编码声明 = re.compile(r"^\s*-\*-\s*coding:\s*[-\w.]+\s*-\*-\s*$", re.IGNORECASE)
代码型注释 = re.compile(r"^(?:!|noqa\b|[A-Za-z_]\w*(?:\.\w+)*\s*=|[\[{\"'])", re.IGNORECASE)
固定元数据注释 = re.compile(r"^(?:Author|Create\s+Date|IsAI):\s*.+$", re.IGNORECASE)


def _应跳过(path: Path, root: Path) -> bool:
    return any(part in 排除目录 for part in path.relative_to(root).parts)


def _需要中文说明(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped and 英文单词.search(stripped) and not 中文字符.search(stripped))


def _文档字符串节点(tree: ast.AST) -> list[ast.Constant]:
    nodes: list[ast.Constant] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            value = body[0].value
            if isinstance(value.value, str):
                nodes.append(value)
    return nodes


def _检查源码文件(path: Path) -> list[str]:
    errors: list[str] = []
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno} 无法解析 Python 源码：{exc.msg}"]

    for node in _文档字符串节点(tree):
        value = str(node.value)
        if _需要中文说明(value):
            errors.append(f"{path}:{node.lineno} 文档字符串缺少简体中文说明")

    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            comment = token.string[1:].strip()
            if (
                编码声明.match(comment)
                or 代码型注释.match(comment)
                or 固定元数据注释.match(comment)
                or not _需要中文说明(comment)
            ):
                continue
            errors.append(f"{path}:{token.start[0]} 注释缺少简体中文说明")
    except tokenize.TokenError as exc:
        errors.append(f"{path} 无法解析注释：{exc.args[0]}")
    return errors


def find_non_chinese_descriptions(root: Path) -> list[str]:
    """返回 Python 注释和文档字符串中的非中文说明。"""
    root = root.resolve()
    errors: list[str] = []
    for path in root.rglob("*.py"):
        if not _应跳过(path, root):
            errors.extend(_检查源码文件(path))
    return sorted(errors)


def _检查技能文件(path: Path) -> list[str]:
    errors: list[str] = []
    in_code_block = False
    in_front_matter = False
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if line == "---":
            in_front_matter = not in_front_matter
            continue
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not line:
            continue
        if in_front_matter and line.split(":", 1)[0] in {"name", "agent_created"}:
            continue
        visible = re.sub(r"`[^`]*`", "", line)
        visible = re.sub(r"\[[^\]]*\]\([^)]*\)", "", visible)
        if _需要中文说明(visible):
            errors.append(f"{path}:{line_number} 技能说明缺少简体中文")
    return errors


def find_non_chinese_skill_text(root: Path) -> list[str]:
    """返回 SKILL 与其随附说明文件中的非中文说明。"""
    root = root.resolve()
    errors: list[str] = []
    for path in root.rglob("*.md"):
        if _应跳过(path, root):
            continue
        relative_parts = path.relative_to(root).parts
        if "skills" in relative_parts:
            errors.extend(_检查技能文件(path))
    return sorted(errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验代码和技能说明是否使用简体中文。")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="待校验的工作区根目录，默认是 api-test。",
    )
    parser.add_argument(
        "--include-skills",
        action="store_true",
        help="同时校验工作区内技能及其随附的 Markdown 说明。",
    )
    args = parser.parse_args()
    errors = find_non_chinese_descriptions(args.root)
    if args.include_skills:
        errors.extend(find_non_chinese_skill_text(args.root))
    if errors:
        print("简体中文说明校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print("简体中文说明校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
