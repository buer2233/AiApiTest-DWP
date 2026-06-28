import ast
import re
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.testcases.models import TestCaseItem
from common.exceptions import InternalServerError


MODULE_NAME_RE = re.compile(r"#\s*Module Name:\s*(?P<name>.+)")


@dataclass(frozen=True)
class ParsedTestCase:
    node_id: str
    package_name: str
    module_name: str
    file_path: str
    class_name: str
    function_name: str
    title: str
    description: str
    markers: list[str]


def _first_string_arg(call: ast.Call) -> str:
    if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
        return call.args[0].value.strip()
    return ""


def _decorator_name(node: ast.AST) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return ""


def _allure_text(function: ast.FunctionDef, decorator_name: str) -> str:
    for decorator in function.decorator_list:
        if isinstance(decorator, ast.Call) and _decorator_name(decorator) == decorator_name:
            return _first_string_arg(decorator)
    return ""


def _markers(function: ast.FunctionDef) -> list[str]:
    names = []
    for decorator in function.decorator_list:
        name = _decorator_name(decorator)
        if name:
            names.append(name)
    return names


def _module_name(source: str, package_name: str) -> str:
    match = MODULE_NAME_RE.search(source)
    return match.group("name").strip() if match else package_name


def _description(function: ast.FunctionDef) -> str:
    return (ast.get_docstring(function) or "").strip()


def _title(function: ast.FunctionDef) -> str:
    allure_title = _allure_text(function, "title") or _allure_text(function, "story")
    if allure_title:
        return allure_title
    description = _description(function)
    return description.splitlines()[0] if description else function.name


def _parse_file(path: Path, source_dir: Path, repo_root: Path) -> list[ParsedTestCase]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    package_name = path.relative_to(source_dir).parts[0]
    module_name = _module_name(source, package_name)
    file_path = path.relative_to(repo_root).as_posix()
    node_path = path.relative_to(source_dir.parent).as_posix()
    cases: list[ParsedTestCase] = []

    def build_case(function: ast.FunctionDef, class_name: str = "") -> ParsedTestCase:
        node_parts = [node_path]
        if class_name:
            node_parts.append(class_name)
        node_parts.append(function.name)
        return ParsedTestCase(
            node_id="::".join(node_parts),
            package_name=package_name,
            module_name=module_name,
            file_path=file_path,
            class_name=class_name,
            function_name=function.name,
            title=_title(function),
            description=_description(function),
            markers=_markers(function),
        )

    for item in tree.body:
        if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
            cases.append(build_case(item))
        if isinstance(item, ast.ClassDef) and item.name.startswith("Test"):
            for method in item.body:
                if isinstance(method, ast.FunctionDef) and method.name.startswith("test_"):
                    cases.append(build_case(method, item.name))
    return cases


def scan_pytest_cases() -> list[ParsedTestCase]:
    source_dir = Path(settings.TEST_CASE_SOURCE_DIR).resolve()
    repo_root = Path(settings.REPO_ROOT).resolve()
    if not source_dir.exists():
        raise InternalServerError("sync_source_missing", "测试用例同步源不存在")

    cases: list[ParsedTestCase] = []
    for path in sorted(source_dir.rglob("test_*.py")):
        try:
            cases.extend(_parse_file(path.resolve(), source_dir, repo_root))
        except (SyntaxError, UnicodeDecodeError):
            # 单个文件解析失败不影响其它用例同步，后续可扩展为审计日志。
            continue
    return cases


def sync_pytest_cases() -> dict[str, int]:
    cases = scan_pytest_cases()
    now = timezone.now()
    seen_node_ids = {case.node_id for case in cases}
    created = 0
    updated = 0

    for case in cases:
        _, was_created = TestCaseItem.objects.update_or_create(
            node_id=case.node_id,
            defaults={
                "package_name": case.package_name,
                "module_name": case.module_name,
                "file_path": case.file_path,
                "class_name": case.class_name,
                "function_name": case.function_name,
                "title": case.title,
                "description": case.description,
                "markers": case.markers,
                "sync_status": TestCaseItem.SyncStatus.SYNCED,
                "last_synced_at": now,
            },
        )
        if was_created:
            created += 1
        else:
            updated += 1

    missing = TestCaseItem.objects.filter(sync_status=TestCaseItem.SyncStatus.SYNCED).exclude(node_id__in=seen_node_ids).update(
        sync_status=TestCaseItem.SyncStatus.MISSING,
        last_synced_at=now,
    )
    return {"created": created, "updated": updated, "missing": missing, "total": created + updated}
