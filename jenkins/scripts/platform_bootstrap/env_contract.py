"""Stage15 根环境配置契约。

该模块只处理键名、顺序和注释结构，不读取或输出任何配置值。
"""

from __future__ import annotations

from pathlib import Path


PRIVATE_SECTION_MARKER = "# === 私有配置（仅本地） ==="

PUBLIC_CONFIG_KEYS = (
    "PLATFORM_BIND_HOST",
    "PLATFORM_PUBLIC_HOST",
    "PLATFORM_PUBLIC_SCHEME",
    "MYSQL_HOST_PORT",
    "JENKINS_HTTP_PORT",
    "JENKINS_AGENT_PORT",
    "BACKEND_HOST_PORT",
    "FRONTEND_HOST_PORT",
    "PROJECT_WORKSPACE",
    "DOCKER_GID",
    "CI_RUN_RETENTION_DAYS",
    "FRONTEND_PLAYWRIGHT_BASE_IMAGE",
)

PRIVATE_ONLY_KEYS = (
    "MYSQL_ROOT_PASSWORD",
    "DB_USER",
    "DB_PASSWORD",
    "DJANGO_SECRET_KEY",
    "AUTH_TOKEN_SECRET",
    "JENKINS_USERNAME",
    "JENKINS_API_TOKEN",
    "INITIAL_ADMIN_USERNAME",
    "INITIAL_ADMIN_DISPLAY_NAME",
    "INITIAL_ADMIN_PASSWORD",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID",
    "JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID",
    "JENKINS_API_TEST_E9_CREDENTIALS_ID",
    "ENVIRONMENT_CATALOG_SERVICE_TOKEN",
)

RETIRED_FIXED_KEYS = (
    "TZ",
    "MYSQL_BIND_HOST",
    "MYSQL_HOST",
    "MYSQL_DATABASE",
    "JENKINS_OPTS",
    "JENKINS_PUBLIC_BASE_URL",
    "JENKINS_API_BASE_URL",
    "JENKINS_EXECUTORS",
    "JENKINS_GENERIC_PIPELINE_JOB_NAME",
    "JENKINS_FAILED_RERUN_JOB_NAME",
    "JENKINS_MODULE_RERUN_JOB_NAME",
    "JENKINS_DAILY_FULL_JOB_PREFIX",
    "JENKINS_DAILY_FULL_JOB_NAME",
    "JENKINS_DAILY_FULL_WORKER_JOB_NAME",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME",
    "JENKINS_ENVIRONMENT_CATALOG_SERVICE_BASE_URL",
    "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME",
    "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED",
    "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES",
    "JENKINS_REQUEST_TIMEOUT_SECONDS",
    "JENKINS_QUEUE_POLL_INTERVAL_SECONDS",
    "JENKINS_BUILD_POLL_INTERVAL_SECONDS",
    "JENKINS_BUILD_POLL_TIMEOUT_SECONDS",
    "JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS",
    "JENKINS_DEFAULT_CASE_PATH",
    "JENKINS_API_TEST_DIR",
    "JENKINS_PYTHON_VENV_DIR",
    "LOCAL_WORKSPACE_REPO",
    "AIAPITEST_LOCAL_WORKSPACE",
    "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS",
    "DJANGO_SETTINGS_MODULE",
    "DJANGO_DEBUG",
    "DJANGO_ALLOWED_HOSTS",
    "DB_ENGINE",
    "DB_CONN_MAX_AGE",
    "AUTH_COOKIE_NAME",
    "AUTH_COOKIE_MAX_AGE_SECONDS",
    "AUTH_COOKIE_SECURE",
    "AUTH_COOKIE_SAMESITE",
    "AUTH_COOKIE_PATH",
    "AUTH_TOKEN_ISSUER",
    "BACKEND_BIND_HOST",
    "BACKEND_SERVICE_URL",
    "BACKEND_API_BASE_URL",
    "FRONTEND_BIND_HOST",
    "FRONTEND_SERVICE_URL",
    "FRONTEND_DEV_HOST",
    "FRONTEND_DEV_PORT",
    "FRONTEND_DEV_API_PROXY_TARGET",
    "VITE_API_BASE_URL",
    "VITE_API_TIMEOUT_MS",
    "VITE_DEV_API_PROXY",
    "PLAYWRIGHT_WEB_SERVER_HOST",
    "PLAYWRIGHT_WEB_SERVER_PORT",
    "PLAYWRIGHT_BASE_URL",
)


def parse_keys(content: str) -> tuple[str, ...]:
    """解析键顺序；赋值右侧永远不进入返回值。"""
    keys: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        keys.append(line.split("=", 1)[0].strip())
    return tuple(keys)


def public_structure(content: str) -> tuple[str, ...]:
    """截断私有区并抹除赋值，保留公共注释、分组和顺序。"""
    structure: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if line.strip() == PRIVATE_SECTION_MARKER:
            break
        if "=" in line and not line.lstrip().startswith("#"):
            structure.append(line.split("=", 1)[0].strip() + "=")
        else:
            structure.append(line)
    return tuple(structure)


def _duplicate_keys(keys: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for key in keys:
        if key in seen and key not in duplicates:
            duplicates.append(key)
        seen.add(key)
    return duplicates


def _sanitize_line(raw_line: str) -> tuple[str | None, str, bool]:
    """立即丢弃赋值右侧，只向调用方返回键名和脱敏结构。"""
    line = raw_line.rstrip("\r\n")
    stripped = line.strip()
    is_private_marker = stripped == PRIVATE_SECTION_MARKER
    if stripped and not stripped.startswith("#") and "=" in line:
        key = line.split("=", 1)[0].strip()
        return key, f"{key}=", is_private_marker
    return None, line, is_private_marker


def _read_contract_structure(
    path: Path,
) -> tuple[tuple[str, ...], dict[str, list[int]], tuple[str, ...]]:
    """流式读取配置，只保留键、行号及公共区脱敏结构。"""
    keys: list[str] = []
    key_lines: dict[str, list[int]] = {}
    structure: list[str] = []
    public_section = True
    with path.open("r", encoding="utf-8") as stream:
        sanitized_lines = map(_sanitize_line, stream)
        for line_number, (key, structure_line, is_private_marker) in enumerate(
            sanitized_lines,
            1,
        ):
            if key is not None:
                keys.append(key)
                key_lines.setdefault(key, []).append(line_number)
            if public_section:
                if is_private_marker:
                    public_section = False
                else:
                    structure.append(structure_line)
    return tuple(keys), key_lines, tuple(structure)


def _first_difference(left: tuple[str, ...], right: tuple[str, ...]) -> int:
    for index, (left_line, right_line) in enumerate(zip(left, right), 1):
        if left_line != right_line:
            return index
    return min(len(left), len(right)) + 1


def validate_contract(env_file: Path, example_file: Path) -> tuple[str, ...]:
    """返回仅含键名/类型的漂移列表；空元组表示契约通过。"""
    if not example_file.is_file():
        return ("missing:.env.example",)
    if not env_file.is_file():
        return ("missing:.env",)

    try:
        env_keys, env_lines, env_structure = _read_contract_structure(env_file)
    except (OSError, UnicodeError):
        return ("read_error:.env",)
    try:
        example_keys, example_lines, example_structure = _read_contract_structure(example_file)
    except (OSError, UnicodeError):
        return ("read_error:.env.example",)
    errors: list[str] = []

    expected_public = set(PUBLIC_CONFIG_KEYS)
    actual_public = set(example_keys)
    for key in sorted(expected_public - actual_public):
        errors.append(f"example:missing:{key}")
    for key in sorted(actual_public - expected_public):
        errors.append(f"example:extra:{key}@line:{example_lines[key][0]}")
    if (
        example_keys != PUBLIC_CONFIG_KEYS
        and len(example_keys) == len(PUBLIC_CONFIG_KEYS)
        and expected_public == actual_public
    ):
        mismatch = _first_difference(example_keys, PUBLIC_CONFIG_KEYS)
        actual_key = example_keys[mismatch - 1]
        expected_key = PUBLIC_CONFIG_KEYS[mismatch - 1]
        errors.append(
            f"example:order:actual:{actual_key}@line:{example_lines[actual_key][0]}:"
            f"expected:{expected_key}"
        )

    env_public_keys = tuple(key for key in env_keys if key in expected_public)
    env_public_order_mismatch = (
        example_keys == PUBLIC_CONFIG_KEYS
        and env_public_keys != PUBLIC_CONFIG_KEYS
        and len(env_public_keys) == len(PUBLIC_CONFIG_KEYS)
        and set(env_public_keys) == expected_public
    )
    if env_public_order_mismatch:
        mismatch = _first_difference(env_public_keys, PUBLIC_CONFIG_KEYS)
        actual_key = env_public_keys[mismatch - 1]
        expected_key = PUBLIC_CONFIG_KEYS[mismatch - 1]
        errors.append(
            f"env:order:actual:{actual_key}@line:{env_lines[actual_key][0]}:"
            f"expected:{expected_key}"
        )
    elif env_structure != example_structure:
        errors.append(
            f"public:order_or_comment@line:{_first_difference(env_structure, example_structure)}"
        )

    expected_env = set(PUBLIC_CONFIG_KEYS + PRIVATE_ONLY_KEYS)
    actual_env = set(env_keys)
    for key in sorted(expected_env - actual_env):
        errors.append(f"env:missing:{key}")
    for key in sorted(actual_env - expected_env):
        errors.append(f"env:extra:{key}@line:{env_lines[key][0]}")

    for path_name, keys, line_map in (
        (".env", env_keys, env_lines),
        (".env.example", example_keys, example_lines),
    ):
        duplicates = _duplicate_keys(keys)
        if duplicates:
            for key in duplicates:
                errors.append(
                    f"duplicate:{path_name}:{key}@line:" + ",".join(map(str, line_map[key]))
                )
    return tuple(errors)
