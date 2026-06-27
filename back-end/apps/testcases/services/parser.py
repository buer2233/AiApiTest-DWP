"""api-test 用例 ast 静态解析器。

纯静态解析，不执行 pytest、不读取源码注释（方案 C）。
解析 test_*.py 中的 test_ 函数与 Test* 类下的 test_ 方法，
提取 node_id、allure title/story/severity 与 docstring 标题。
"""
import ast
from pathlib import Path


def _const_str(node):
    """取字符串常量值。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _severity_value(node):
    """allure.severity_level.CRITICAL → 'critical'；字符串字面量也兼容。"""
    if isinstance(node, ast.Attribute):
        return node.attr.lower()
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.lower()
    return None


def _extract_allure(decorator_list):
    """从装饰器列表提取 (title, story, severity)。"""
    title = story = severity = None
    for dec in decorator_list:
        if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
            continue
        attr = dec.func.attr
        if attr == "title" and dec.args:
            title = _const_str(dec.args[0])
        elif attr == "story" and dec.args:
            story = _const_str(dec.args[0])
        elif attr == "severity" and dec.args:
            severity = _severity_value(dec.args[0])
    return title, story, severity


def _first_nonempty_line(doc):
    """docstring 首个非空行（跳过开头空白行）。"""
    if not doc:
        return ""
    for line in doc.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _resolve_title(title, story, doc):
    """标题优先级：title > story > docstring 首个非空行。"""
    return title or story or _first_nonempty_line(doc) or ""


def _is_test_func(node):
    return isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
        "test_"
    )


def _build_item(func_node, class_name, module_key, case_path, node_prefix):
    title, story, severity = _extract_allure(func_node.decorator_list)
    doc = ast.get_docstring(func_node)
    case_title = _resolve_title(title, story, doc)
    if class_name:
        node_id = f"{node_prefix}::{class_name}::{func_node.name}"
    else:
        node_id = f"{node_prefix}::{func_node.name}"
    return {
        "module_key": module_key,
        "module_name": module_key,  # 第一版同 module_key
        "case_path": case_path,
        "node_id": node_id,
        "function_name": func_node.name,
        "class_name": class_name,
        "case_title": case_title,
        "story": story or "",
        "severity": severity or "",
    }


def parse_directory(case_root, path_prefix="test_case"):
    """静态解析 case_root 下所有 test_*.py。

    - node_id / case_path 以 path_prefix 开头（默认 'test_case'）。
    - module_key 取相对 case_root 的第一级目录名；文件直属时取文件 stem。
    - 参数化用例按函数级记录一条（node_id 不含 [param] 后缀）。
    """
    case_root = Path(case_root)
    results = []
    if not case_root.is_dir():
        return results
    for py_file in sorted(case_root.rglob("test_*.py")):
        rel = py_file.relative_to(case_root)
        rel_posix = rel.as_posix()
        parts = rel.parts
        module_key = parts[0] if len(parts) >= 2 else py_file.stem
        case_path = f"{path_prefix}/{rel_posix}"
        node_prefix = f"{path_prefix}/{rel_posix}"
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            # 跳过无法解析的文件，保证整体同步不崩溃
            continue
        for node in tree.body:
            if _is_test_func(node):
                results.append(_build_item(node, None, module_key, case_path, node_prefix))
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for sub in node.body:
                    if _is_test_func(sub):
                        results.append(
                            _build_item(sub, node.name, module_key, case_path, node_prefix)
                        )
    return results
