# -*- coding: utf-8 -*-
"""从 SVN diff / Java 源码提取变更分类、符号和 HTTP 入口。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

UI_EXTS = {".jsp", ".js", ".css", ".html", ".htm", ".vue", ".tsx", ".jsx", ".less", ".scss"}
SQL_EXTS = {".sql"}
HTTP_ANNOTATIONS = ("GET", "POST", "PUT", "DELETE", "PATCH")

# 阶段 A 纯前端判定层（与 kind=api/ui/sql/other 正交）
LAYER_FRONTEND = "frontend"
LAYER_BACKEND = "backend"
LAYER_AMBIGUOUS = "ambiguous"
PURE_FRONTEND_MESSAGE = "纯前端改动，无接口回归项"
FRONTEND_LAYER_EXTS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".css",
    ".less",
    ".scss",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}
AMBIGUOUS_LAYER_EXTS = {".jsp", ".ftl", ".xml", ".properties", ".vm"}

_PATH_LIT = re.compile(r'@Path\(\s*"([^"]+)"\s*\)')
_HTTP_ANN = re.compile(r"@(GET|POST|PUT|DELETE|PATCH)\b")
_CLASS_DECL = re.compile(
    r"(?:public|protected|private)?\s*(?:abstract\s+|final\s+)?class\s+(\w+)"
)
_METHOD_DECL = re.compile(
    r"(?:public|protected|private)\s+(?:static\s+)?[\w.<>,\[\]?]+\s+(\w+)\s*\("
)
_DIFF_INDEX = re.compile(r"^Index:\s+(.+)$", re.M)
_DIFF_PLUS = re.compile(r"^\+\+\+\s+([^\t\s]+)")
_DIFF_MINUS = re.compile(r"^---\s+([^\t\s]+)")

# 四期 T4.1：端点提取治理
# E9 的 HTTP 入口命名后缀：旧式 *Action（com.api.*.web）占多数，
# 新式 *Controller（com.api.*.controller）与个别 *Resource 同样存在。
ENTRY_NAME_SUFFIXES = ("Controller", "Action", "Resource")
ENTRYPOINT_RULES_VERSION = "t4.1-v1"
# 端点发现策略标记，写入 endpoint["via"] 与诊断记录
VIA_DIRECT = "direct"
VIA_FACADE = "facade"
VIA_INHERIT = "inherit"
VIA_CALLER_SCAN = "caller_scan"
VIA_STRUTS = "struts_config"
VIA_MCP = "mcp_refs"
# 调用方扫描时最多解析的候选文件数，避免公共类引发全库精读
CALLER_SCAN_MAX_FILES = 25
# 继承链向上解析类级 @Path 的最大层数
INHERIT_MAX_DEPTH = 3
_EXTENDS_DECL = re.compile(r"\bclass\s+\w+\s+extends\s+([\w.]+)")
_STRUTS_ACTION = re.compile(r"<action\s+([^>]*)>", re.I)
_STRUTS_ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def posix_path(path: str) -> str:
    return (path or "").replace("\\", "/").lstrip("./")


def classify_file(path: str, source: str | None = None) -> str:
    """按路径（及可选源码）将变更文件分成 api / ui / sql / other。"""
    text = posix_path(path)
    ext = Path(text).suffix.lower()
    if ext in SQL_EXTS:
        return "sql"
    if ext in UI_EXTS:
        return "ui"
    if ext == ".java":
        name = Path(text).name.lower()
        if name.endswith("action.java") or "/web/" in text.lower():
            return "api"
        if source and ("@Path(" in source or "@GET" in source or "@POST" in source):
            return "api"
        return "other"
    return "other"


def classify_change_layer(path: str) -> str:
    """将变更文件分成 frontend / backend / ambiguous，供纯前端判定使用。

    后端：``src/**`` 下的 Java 及其他非前端源码、``classbean/**`` 编译产物。
    前端：JS/TS/CSS/HTML 及图片、字体等静态资源。
    模糊：JSP/FTL、``WEB-INF/**``、xml/properties/vm 等配置模板；无法归类的文件也按模糊处理。
    """
    text = posix_path(path).lstrip("/")
    lower = text.lower()
    ext = Path(lower).suffix
    if not text:
        return LAYER_AMBIGUOUS
    if lower.startswith("web-inf/") or "/web-inf/" in lower:
        return LAYER_AMBIGUOUS
    if lower.startswith("classbean/") or "/classbean/" in lower:
        return LAYER_BACKEND
    if ext in AMBIGUOUS_LAYER_EXTS:
        return LAYER_AMBIGUOUS
    if ext in FRONTEND_LAYER_EXTS:
        return LAYER_FRONTEND
    if lower.startswith("src/") or "/src/" in f"/{lower}":
        return LAYER_BACKEND
    return LAYER_AMBIGUOUS


def change_layer_of(item: str | dict[str, Any]) -> str:
    """读取已标注的 change_layer，缺失时按路径重新判定。"""
    if isinstance(item, str):
        return classify_change_layer(item)
    layer = item.get("change_layer") or ""
    if layer in {LAYER_FRONTEND, LAYER_BACKEND, LAYER_AMBIGUOUS}:
        return layer
    return classify_change_layer(str(item.get("path") or ""))


def is_pure_frontend(changed_files: Iterable[str | dict[str, Any]] | None) -> bool:
    """仅当存在变更文件且全部属于前端层时返回 True。空列表按非纯前端处理。"""
    files = list(changed_files or [])
    if not files:
        return False
    return all(change_layer_of(item) == LAYER_FRONTEND for item in files)


def class_name_from_path(path: str) -> str | None:
    name = Path(posix_path(path)).stem
    return name or None


def parse_diff_files(diff_text: str) -> list[str]:
    """从 unified diff 中收集变更文件路径。"""
    files: list[str] = []
    seen: set[str] = set()
    for match in _DIFF_INDEX.finditer(diff_text or ""):
        path = _strip_diff_path(match.group(1))
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    if files:
        return files
    for line in (diff_text or "").splitlines():
        plus = _DIFF_PLUS.match(line)
        minus = _DIFF_MINUS.match(line)
        raw = plus.group(1) if plus else (minus.group(1) if minus else "")
        path = _strip_diff_path(raw)
        if path and path not in seen and path != "/dev/null":
            seen.add(path)
            files.append(path)
    return files


def _strip_diff_path(path: str) -> str:
    text = posix_path(path)
    if text.startswith("a/") or text.startswith("b/"):
        text = text[2:]
    return text


def extract_symbols_from_diff(diff_text: str) -> list[dict[str, str]]:
    """从 diff 提取 class / method 符号。每个变更 Java 文件的路径 stem 都作为兜底 class。"""
    symbols: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    touched_java_files: list[str] = []
    current_file = ""
    current_class = ""
    for line in (diff_text or "").splitlines():
        index = _DIFF_INDEX.match(line)
        if index:
            current_file = _strip_diff_path(index.group(1))
            current_class = class_name_from_path(current_file) or ""
            _register_touched_java_file(touched_java_files, current_file)
            continue
        plus = _DIFF_PLUS.match(line)
        if plus:
            current_file = _strip_diff_path(plus.group(1))
            current_class = class_name_from_path(current_file) or ""
            _register_touched_java_file(touched_java_files, current_file)
            continue
        payload = line[1:] if line[:1] in "+- " else line
        class_match = _CLASS_DECL.search(payload)
        if class_match:
            current_class = class_match.group(1)
            _add_symbol(symbols, seen, current_class, current_file, "class")
        if current_file.lower().endswith(".java"):
            method_match = _METHOD_DECL.search(payload)
            if method_match:
                name = method_match.group(1)
                if name not in {"if", "for", "while", "switch", "catch"}:
                    _add_symbol(symbols, seen, name, current_file, "method")
                    if current_class:
                        _add_symbol(
                            symbols,
                            seen,
                            f"{current_class}.{name}",
                            current_file,
                            "method",
                        )
    if current_file and current_class:
        _add_symbol(symbols, seen, current_class, current_file, "class")
    # 兜底：diff 触及的每个 Java 文件都保留路径 stem 类符号，
    # 避免 hunk 无类声明时只保留最后一个文件的类（r349149 回归）。
    for file_path in touched_java_files:
        class_name = class_name_from_path(file_path)
        if class_name:
            _add_symbol(symbols, seen, class_name, file_path, "class")
    return symbols


def _register_touched_java_file(touched: list[str], file_path: str) -> None:
    """登记 diff 触及的 Java 文件，保持出现顺序且不重复。"""
    if file_path.lower().endswith(".java") and file_path not in touched:
        touched.append(file_path)


def _add_symbol(
    symbols: list[dict[str, str]],
    seen: set[tuple[str, str, str]],
    name: str,
    file_path: str,
    kind: str,
) -> None:
    key = (name, file_path, kind)
    if not name or key in seen:
        return
    seen.add(key)
    symbols.append({"name": name, "file": file_path, "kind": kind})


def join_api_url(class_path: str | None, method_path: str | None) -> str:
    """拼接 E9 JAX-RS 路径，缺 /api 前缀时补上。"""
    parts: list[str] = []
    for raw in (class_path, method_path):
        if not raw:
            continue
        piece = raw.strip()
        if not piece.startswith("/"):
            piece = "/" + piece
        parts.append(piece.rstrip("/") or "")
    url = "".join(parts) or "/"
    if url == "/":
        return "/api"
    if url == "/api" or url.startswith("/api/") or url.startswith("/api"):
        if url.startswith("/api") and not url.startswith("/api/"):
            return url
        return url
    return "/api" + url


def extract_class_path(source: str) -> str | None:
    """取 class 声明之前最后一个 @Path。"""
    class_match = re.search(r"\bclass\s+\w+", source or "")
    header = source[: class_match.start()] if class_match else (source or "")
    matches = _PATH_LIT.findall(header)
    return matches[-1] if matches else None


def extract_jaxrs_methods(source: str) -> list[dict[str, str]]:
    """扫描方法级 @GET/@POST + @Path + 方法名。"""
    http: str | None = None
    path: str | None = None
    methods: list[dict[str, str]] = []
    in_class = False
    for line in (source or "").splitlines():
        if not in_class:
            if re.search(r"\bclass\s+\w+", line):
                in_class = True
            continue
        http_match = _HTTP_ANN.search(line)
        if http_match:
            http = http_match.group(1)
        path_match = _PATH_LIT.search(line)
        if path_match:
            path = path_match.group(1)
        method_match = _METHOD_DECL.search(line)
        if method_match and (http or path):
            methods.append(
                {
                    "http_method": http or "GET",
                    "path": path or "",
                    "name": method_match.group(1),
                }
            )
            http = None
            path = None
    return methods


def find_api_facade(repo: Path, changed_path: str, class_name: str) -> Path | None:
    """按 E9 惯例找 com.api.*.web 同名 Action。"""
    posix = posix_path(changed_path)
    candidates: list[Path] = []
    if "/com/engine/" in posix:
        swapped = posix.replace("/com/engine/", "/com/api/", 1)
        candidate = repo / swapped
        if candidate.is_file():
            candidates.append(candidate)
    api_root = repo / "src" / "com" / "api"
    if class_name and api_root.is_dir():
        candidates.extend(api_root.rglob(f"{class_name}.java"))
    seen: set[Path] = set()
    for item in candidates:
        resolved = item.resolve()
        if resolved in seen or not item.is_file():
            continue
        seen.add(resolved)
        return item
    return None


def endpoints_from_java_files(
    repo: Path,
    file_paths: Iterable[str],
    read_text=None,
    diagnostics: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """从变更 Java 文件及其 api facade 提取 HTTP 入口。

    四期 T4.1 起按策略分层提取，并在 ``diagnostics`` 中留痕：
    1. direct —— 变更文件自身的类级/方法级 JAX-RS 注解；
    2. facade —— E9 惯例的 com.engine → com.api 同名 Action/Controller；
    3. inherit —— 类声明 extends 链向上解析类级 @Path；
    4. caller_scan —— 以上均无果时，扫描引用本类的候选入口文件
       （r349155 类提交：只改 Service，入口在同模块 Controller）。
    任一策略产出的端点都会带 ``via`` 字段说明发现来源；诊断信息写入
    ``diagnostics``（若提供），端点为空时不再静默结束。
    """
    reader = read_text or _read_text
    endpoints: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for rel in file_paths:
        posix = posix_path(rel)
        if not posix.lower().endswith(".java"):
            continue
        abs_path = repo / posix
        source = reader(abs_path)
        class_name = class_name_from_path(posix) or ""
        class_path = extract_class_path(source) if source else None
        methods = extract_jaxrs_methods(source) if source else []
        via = VIA_DIRECT
        strategies: list[str] = [VIA_DIRECT]

        facade = find_api_facade(repo, posix, class_name)
        facade_path = None
        if facade is not None:
            strategies.append(VIA_FACADE)
            facade_source = reader(facade)
            facade_path = extract_class_path(facade_source) if facade_source else None
            if not methods and facade_source:
                facade_methods = extract_jaxrs_methods(facade_source)
                if facade_methods:
                    methods = facade_methods
                    via = VIA_FACADE

        effective_class_path = class_path or facade_path
        if effective_class_path is None and source:
            strategies.append(VIA_INHERIT)
            inherited = resolve_inherited_class_path(repo, source, read_text=reader)
            if inherited:
                effective_class_path = inherited
                # 方法注解哪怕是自身的，URL 也依赖继承链解析出的类级 @Path
                via = VIA_INHERIT
        elif facade_path and not class_path and via == VIA_DIRECT:
            # 方法注解来自自身、类级 @Path 来自 facade 的混合场景
            via = VIA_FACADE

        if not methods and effective_class_path:
            methods = [{"http_method": "GET", "path": "", "name": class_name}]

        before = len(endpoints)
        for method in methods:
            url = join_api_url(effective_class_path, method.get("path"))
            action = f"{class_name}.{method['name']}" if class_name else method["name"]
            _add_endpoint(endpoints, seen, method.get("http_method") or "GET", url, action, via, posix)

        # 兜底：自身与 facade/继承都没有产出端点时，逐级反查引用本类的入口文件。
        # 窄范围命中的调用方若解析不出端点（如兄弟 Service），继续扩大范围。
        if len(endpoints) == before and class_name:
            strategies.append(VIA_CALLER_SCAN)
            for scope in caller_scan_scopes(posix):
                caller_files = find_caller_files_in_scope(
                    repo, scope, class_name, posix, read_text=reader
                )
                for caller_rel in caller_files:
                    caller_source = reader(repo / caller_rel)
                    caller_class = class_name_from_path(caller_rel) or ""
                    caller_class_path = extract_class_path(caller_source) if caller_source else None
                    caller_methods = extract_jaxrs_methods(caller_source) if caller_source else []
                    caller_before = len(endpoints)
                    for method in caller_methods:
                        url = join_api_url(caller_class_path, method.get("path"))
                        action = f"{caller_class}.{method['name']}" if caller_class else method["name"]
                        _add_endpoint(
                            endpoints,
                            seen,
                            method.get("http_method") or "GET",
                            url,
                            action,
                            VIA_CALLER_SCAN,
                            caller_rel,
                            changed_file=posix,
                        )
                    if len(endpoints) == caller_before:
                        _record_candidate(
                            diagnostics,
                            caller_rel,
                            caller_class,
                            "引用了变更类但自身未解析出端点",
                        )
                if len(endpoints) > before:
                    break

        found = len(endpoints) - before
        _record_attempt(diagnostics, posix, strategies, found)
    return endpoints


def _add_endpoint(
    endpoints: list[dict[str, str]],
    seen: set[tuple[str, str, str]],
    http_method: str,
    url: str,
    action: str,
    via: str,
    source_file: str,
    changed_file: str | None = None,
) -> None:
    """登记一条端点；key 不含 via，保证不同策略发现的同一入口只保留首条。"""
    key = (http_method, url, action)
    if key in seen:
        return
    seen.add(key)
    item: dict[str, str] = {
        "method": http_method,
        "url": url,
        "action": action,
        "via": via,
        "source_file": source_file,
    }
    if changed_file:
        item["changed_file"] = changed_file
    endpoints.append(item)


def caller_scan_scopes(changed_path: str) -> list[Path]:
    """返回逐级上溯的调用方扫描范围（最窄在前）。

    从变更文件所在目录开始，上溯到 src/com/api 或 src/com/engine 边界；
    最后补一个 src/com/api 兜底范围。调用方在窄范围命中但解析不出端点时，
    调用方可继续尝试更宽范围（r349155 回归：同目录的兄弟 Service 不是入口）。
    """
    boundaries = {Path("src") / "com" / "api", Path("src") / "com" / "engine"}
    scopes: list[Path] = []
    parent = Path(posix_path(changed_path)).parent
    while str(parent) not in {".", ""} and len(parent.parts) >= 3:
        scopes.append(parent)
        if parent in boundaries:
            break
        parent = parent.parent
    fallback = Path("src") / "com" / "api"
    if fallback not in scopes:
        scopes.append(fallback)
    return scopes


def find_caller_files_in_scope(
    repo: Path,
    scope: Path,
    class_name: str,
    changed_path: str,
    read_text=None,
    max_matches: int = CALLER_SCAN_MAX_FILES,
) -> list[str]:
    """在单个范围内查找引用 ``class_name`` 的 Java 文件（排除变更文件自身）。"""
    if not class_name:
        return []
    reader = read_text or _read_text
    pattern = re.compile(r"\b" + re.escape(class_name) + r"\b")
    changed = posix_path(changed_path)
    root = repo / scope
    if not root.is_dir():
        return []
    matches: list[str] = []
    for path in sorted(root.rglob("*.java")):
        rel = str(path.relative_to(repo)).replace("\\", "/")
        if rel == changed:
            continue
        text = reader(path)
        if text and pattern.search(text):
            matches.append(rel)
            if len(matches) >= max_matches:
                break
    return matches


def find_caller_files(
    repo: Path,
    class_name: str,
    changed_path: str,
    read_text=None,
    max_matches: int = CALLER_SCAN_MAX_FILES,
) -> list[str]:
    """逐级扩大范围查找引用 ``class_name`` 的候选文件，任一层级命中即返回。

    供端点提取之外的调用方（如 T4.2 证据包）直接使用；端点提取内部用
    ``caller_scan_scopes`` + ``find_caller_files_in_scope`` 逐级尝试，
    以便窄范围命中非入口类时继续扩大搜索。
    """
    for scope in caller_scan_scopes(changed_path):
        matches = find_caller_files_in_scope(
            repo, scope, class_name, changed_path, read_text, max_matches
        )
        if matches:
            return matches
    return []


def resolve_inherited_class_path(repo: Path, source: str, read_text=None, depth: int = INHERIT_MAX_DEPTH) -> str | None:
    """沿 extends 链向上查找类级 @Path，用于控制器继承场景。"""
    reader = read_text or _read_text
    current = source or ""
    for _ in range(depth):
        match = _EXTENDS_DECL.search(current)
        if not match:
            return None
        parent = match.group(1).split(".")[-1]
        src_root = repo / "src"
        candidates = sorted(src_root.rglob(f"{parent}.java"))[:3] if src_root.is_dir() else []
        if not candidates:
            return None
        current = reader(candidates[0]) or ""
        path = extract_class_path(current)
        if path:
            return path
    return None


def struts_endpoints_for_classes(
    repo: Path,
    class_names: Iterable[str],
    read_text=None,
) -> list[dict[str, str]]:
    """在 WEB-INF/struts-config.xml 中查找 type 命中变更类名的 Action 映射。

    E9 主体已迁到 JAX-RS，struts 映射只作为兜底候选；命中的条目按
    ``POST /api<path>.do`` 规范化，action 记为 ``<Type>.<parameter>``。
    """
    reader = read_text or _read_text
    config = repo / "WEB-INF" / "struts-config.xml"
    if not config.is_file():
        return []
    text = reader(config)
    if not text:
        return []
    wanted = {name for name in class_names if name}
    if not wanted:
        return []
    endpoints: list[dict[str, str]] = []
    for block in _STRUTS_ACTION.finditer(text):
        attrs = dict(_STRUTS_ATTR.findall(block.group(1)))
        type_full = attrs.get("type") or ""
        type_name = type_full.split(".")[-1]
        if type_name not in wanted:
            continue
        path = attrs.get("path") or ""
        if not path:
            continue
        parameter = attrs.get("parameter") or "execute"
        endpoints.append(
            {
                "method": "POST",
                "url": f"/api{path}.do",
                "action": f"{type_name}.{parameter}",
                "via": VIA_STRUTS,
                "source_file": "WEB-INF/struts-config.xml",
            }
        )
    return endpoints


def new_endpoint_diagnostics(skipped: str | None = None) -> dict[str, Any]:
    """构造 endpoint_diagnostics 初始结构。

    ``skipped`` 非空表示整段提取被跳过（如纯前端提交）；其余字段在提取
    过程中累积，端点为空时由 finalize_endpoint_diagnostics 给出人工复核标记。
    """
    payload: dict[str, Any] = {
        "rules_version": ENTRYPOINT_RULES_VERSION,
        "needs_manual_review": False,
        "skipped": skipped,
        "attempts": [],
        "candidates": [],
        "notes": [],
    }
    return payload


def _record_attempt(
    diagnostics: dict[str, Any] | None,
    file_path: str,
    strategies: list[str],
    found: int,
) -> None:
    if diagnostics is None:
        return
    diagnostics.setdefault("attempts", []).append(
        {"file": file_path, "strategies": strategies, "endpoints_found": found}
    )


def _record_candidate(
    diagnostics: dict[str, Any] | None,
    file_path: str,
    class_name: str,
    reason: str,
) -> None:
    if diagnostics is None:
        return
    candidates = diagnostics.setdefault("candidates", [])
    if any(item.get("file") == file_path for item in candidates):
        return
    candidates.append({"file": file_path, "class": class_name, "reason": reason})


def finalize_endpoint_diagnostics(
    diagnostics: dict[str, Any],
    endpoints: list[dict[str, str]],
    changed_files: list[dict[str, Any]],
) -> dict[str, Any]:
    """端点收尾：为空且存在后端 Java 变更时标记人工复核并给出候选。

    返回更新后的诊断结构。候选入口优先取尝试过的 Java 文件本身，
    方便人工按文件反查；纯前端等已跳过场景不做标记。
    """
    if diagnostics.get("skipped"):
        return diagnostics
    if endpoints:
        return diagnostics
    backend_java = [
        item
        for item in changed_files
        if str(item.get("path") or "").lower().endswith(".java")
        and item.get("change_layer") != LAYER_FRONTEND
    ]
    if not backend_java:
        diagnostics["notes"].append("无后端 Java 变更，未执行端点提取兜底。")
        return diagnostics
    diagnostics["needs_manual_review"] = True
    for item in backend_java:
        _record_candidate(
            diagnostics,
            item.get("path") or "",
            class_name_from_path(item.get("path") or "") or "",
            "变更文件未解析出 JAX-RS 注解，需人工确认 HTTP 入口",
        )
    diagnostics["notes"].append(
        "端点提取为空：已尝试直接解析、facade、继承链与调用方扫描；"
        "请根据 candidates 人工复核，或补充 MCP callers 证据。"
    )
    return diagnostics


def endpoints_from_action_refs(
    repo: Path,
    refs: Iterable[dict[str, str]],
    read_text=None,
) -> list[dict[str, str]]:
    """根据 MCP 抓到的 XxxAction.method 再解析 URL。"""
    reader = read_text or _read_text
    endpoints: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    api_root = repo / "src" / "com" / "api"
    engine_root = repo / "src" / "com" / "engine"
    for ref in refs:
        action = ref.get("action") or ""
        method_name = ref.get("method") or ""
        if not action:
            continue
        java_name = f"{action}.java"
        files: list[Path] = []
        for root in (api_root, engine_root):
            if root.is_dir():
                files.extend(root.rglob(java_name))
        if not files:
            continue
        extracted = endpoints_from_java_files(
            repo,
            [str(path.relative_to(repo)).replace("\\", "/") for path in files],
            read_text=reader,
        )
        for item in extracted:
            if method_name and not item["action"].endswith("." + method_name):
                if item["action"] != f"{action}.{method_name}":
                    # 保留同 Action 的全部方法，但优先匹配同名方法
                    continue
            key = (item["method"], item["url"], item["action"])
            if key in seen:
                continue
            seen.add(key)
            endpoints.append(item)
        if method_name and not any(e["action"].endswith("." + method_name) for e in extracted):
            # 方法名对不上时退回该 Action 全部入口
            for item in extracted:
                key = (item["method"], item["url"], item["action"])
                if key in seen:
                    continue
                seen.add(key)
                endpoints.append(item)
    return endpoints


def diff_excerpt(diff_text: str, max_lines: int = 80) -> str:
    lines = (diff_text or "").splitlines()
    excerpt = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        excerpt += f"\n... ({len(lines) - max_lines} more lines)"
    return excerpt


def compute_confidence(warnings: list[str], endpoints: list[Any], changed_files: list[dict]) -> str:
    if any("svn" in (item or "").lower() and "失败" in (item or "") for item in warnings):
        return "low"
    if warnings:
        return "medium"
    if endpoints:
        return "high"
    if any(item.get("kind") == "api" for item in changed_files):
        return "medium"
    return "medium"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# ---------------------------------------------------------------------------
# SVN log XML 解析工具（从 svn_ops 迁入，供测试使用）
# ---------------------------------------------------------------------------

import xml.etree.ElementTree as ET  # noqa: E402


def parse_log_xml(xml_text: str) -> dict[str, Any]:
    """解析 svn log XML 为结构化提交信息。"""
    root = ET.fromstring(xml_text)
    entry = root.find("logentry")
    if entry is None:
        raise ValueError("svn log XML 中没有 logentry")
    revision = int(entry.attrib.get("revision", "0"))
    paths: list[dict[str, str]] = []
    for path_el in entry.findall("paths/path"):
        paths.append(
            {
                "path": _normalize_repo_path(path_el.text or ""),
                "action": path_el.attrib.get("action", ""),
                "kind": path_el.attrib.get("kind", ""),
            }
        )
    return {
        "revision": revision,
        "author": (entry.findtext("author") or "").strip(),
        "date": (entry.findtext("date") or "").strip(),
        "message": (entry.findtext("msg") or "").strip(),
        "paths": paths,
    }


def _normalize_repo_path(path: str) -> str:
    """去掉仓库前缀，得到相对路径。"""
    text = (path or "").replace("\\", "/").lstrip("/")
    for prefix in ("ecology/trunk/", "svn/ecology/trunk/", "trunk/"):
        if text.startswith(prefix):
            return text[len(prefix) :]
    return text
