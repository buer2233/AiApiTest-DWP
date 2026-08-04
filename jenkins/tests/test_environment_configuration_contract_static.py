"""Stage15 环境配置契约的静态门禁。

测试只比较键名、顺序和注释结构，不读取或拼接私有配置值，避免失败输出泄露凭据。
"""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE_FILE = ROOT / ".env.example"
from jenkins.scripts.platform_bootstrap.env_contract import (
    PRIVATE_ONLY_KEYS,
    PRIVATE_SECTION_MARKER,
    PUBLIC_CONFIG_KEYS,
    RETIRED_FIXED_KEYS,
    parse_keys,
    public_structure,
    validate_contract,
)


def _read(path: Path) -> str:
    assert path.is_file(), f"缺少配置文件：{path.name}"
    return path.read_text(encoding="utf-8")


def _parse_keys(content: str) -> tuple[str, ...]:
    return parse_keys(content)


def _public_structure(content: str) -> tuple[str, ...]:
    return public_structure(content)


def _synthetic_private_content(example: str) -> str:
    """构造只含测试哨兵值的私有配置，任何失败都不会接触真实凭据。"""
    private_lines = [f"{key}=synthetic-{index}" for index, key in enumerate(PRIVATE_ONLY_KEYS, 1)]
    return example.rstrip() + "\n" + "\n".join(private_lines) + "\n"


def test_template_contains_exactly_frozen_public_keys() -> None:
    """模板只允许出现冻结的公共键，且顺序必须稳定。"""
    actual = _parse_keys(_read(ENV_EXAMPLE_FILE))
    assert actual == PUBLIC_CONFIG_KEYS


def test_private_file_contains_private_keys_and_public_projection_matches_template(tmp_path) -> None:
    """合成私有文件始终验契约；宿主机私有文件存在时再附加验证。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    synthetic_example = tmp_path / ".env.example"
    synthetic_private = tmp_path / ".env"
    synthetic_example.write_text(example_content, encoding="utf-8")
    synthetic_private.write_text(_synthetic_private_content(example_content), encoding="utf-8")

    assert validate_contract(synthetic_private, synthetic_example) == ()
    if ENV_FILE.is_file():
        assert validate_contract(ENV_FILE, ENV_EXAMPLE_FILE) == ()


def test_private_only_keys_never_appear_in_template() -> None:
    """账号、密码、token、密钥和内部同步配置不能进入可提交模板。"""
    example_keys = set(_parse_keys(_read(ENV_EXAMPLE_FILE)))
    assert example_keys.isdisjoint(PRIVATE_ONLY_KEYS)


def test_template_contains_private_section_marker_without_private_keys() -> None:
    """首次复制模板后可直接在标记下补私有键，且模板本身不公开私有项。"""
    example = _read(ENV_EXAMPLE_FILE)

    assert PRIVATE_SECTION_MARKER in example
    assert example.count(PRIVATE_SECTION_MARKER) == 1


def test_retired_fixed_keys_are_absent_from_template_and_rejected_in_private_file(tmp_path) -> None:
    """固定项不得出现在模板，注入合成私有文件后必须被契约拒绝。"""
    assert "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME" in RETIRED_FIXED_KEYS
    example_content = _read(ENV_EXAMPLE_FILE)
    example_keys = set(_parse_keys(example_content))
    assert example_keys.isdisjoint(RETIRED_FIXED_KEYS)
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(example_content, encoding="utf-8")
    private.write_text(
        _synthetic_private_content(example_content)
        + "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME=synthetic-retired\n",
        encoding="utf-8",
    )

    issues = validate_contract(private, example)

    assert "env:extra:JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME" in issues[0]
    assert "synthetic-retired" not in "\n".join(issues)


def test_compose_does_not_interpolate_retired_fixed_keys() -> None:
    """Compose 不得继续把固定默认值伪装成可配置项。"""
    compose = _read(ROOT / "docker-compose.yml")
    for key in RETIRED_FIXED_KEYS:
        assert f"${{{key}:" not in compose
        assert f"${{{key}}}" not in compose


def test_public_keys_are_not_only_documentation_placeholders() -> None:
    """每个公共键都必须在实现入口中出现，而不是只停留在模板说明。"""
    implementation = "\n".join(
        _read(ROOT / relative)
        for relative in (
            "docker-compose.yml",
            "back-end/config/settings/base.py",
            "front-end/config/env.ts",
            "jenkins/scripts/platform_bootstrap/preflight.py",
            "jenkins/scripts/platform_bootstrap/jenkins_api.py",
            "scripts/deploy-docker.ps1",
            "scripts/deploy-docker.sh",
        )
    )
    missing = [key for key in PUBLIC_CONFIG_KEYS if key not in implementation]
    assert not missing, f"公共键没有生产消费者：{missing}"


def test_private_values_are_not_required_in_template() -> None:
    """模板可以被提交，私有文件才承担凭据与初始化账号。"""
    example = _read(ENV_EXAMPLE_FILE)
    forbidden_fragments = (
        "MYSQL_ROOT_PASSWORD=",
        "DB_PASSWORD=",
        "DJANGO_SECRET_KEY=",
        "AUTH_TOKEN_SECRET=",
        "JENKINS_API_TOKEN=",
        "INITIAL_ADMIN_PASSWORD=",
        "ENVIRONMENT_CATALOG_SERVICE_TOKEN=",
    )
    for fragment in forbidden_fragments:
        assert fragment not in example


@pytest.mark.parametrize(
    ("mutator", "expected_issue"),
    [
        (lambda lines: lines[:-1], "missing"),
        (lambda lines: lines + ["UNKNOWN_PRIVATE_OPTION=value"], "extra"),
        (lambda lines: lines + [lines[-1]], "duplicate"),
        (lambda lines: [*lines[:2], lines[3], lines[2], *lines[4:]], "order_or_comment"),
    ],
    ids=["missing", "extra", "duplicate", "order"],
)
def test_contract_reports_structural_drift_without_values(tmp_path, mutator, expected_issue) -> None:
    """契约错误只报告结构、键名和行号，不得回显赋值。"""
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(_read(ENV_EXAMPLE_FILE), encoding="utf-8")
    original = _synthetic_private_content(_read(ENV_EXAMPLE_FILE)).splitlines()
    private.write_text("\n".join(mutator(original)) + "\n", encoding="utf-8")

    issues = validate_contract(private, example)

    assert issues
    assert any(expected_issue in issue for issue in issues)
    serialized = "\n".join(issues)
    for index in range(1, len(PRIVATE_ONLY_KEYS) + 1):
        assert f"synthetic-{index}" not in serialized


def test_contract_reports_frozen_key_order_with_actual_expected_key_and_line(tmp_path) -> None:
    """两文件同步错序时也必须指出首个错位键和实际行号，不得只返回 order。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    lines = example_content.splitlines()
    first_index = next(index for index, line in enumerate(lines) if line.startswith("PLATFORM_BIND_HOST="))
    second_index = next(index for index, line in enumerate(lines) if line.startswith("PLATFORM_PUBLIC_HOST="))
    lines[first_index], lines[second_index] = lines[second_index], lines[first_index]
    reordered_example = "\n".join(lines) + "\n"
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(reordered_example, encoding="utf-8")
    private.write_text(_synthetic_private_content(reordered_example), encoding="utf-8")

    issues = validate_contract(private, example)

    assert issues == (
        f"example:order:actual:PLATFORM_PUBLIC_HOST@line:{first_index + 1}:"
        "expected:PLATFORM_BIND_HOST",
    )


def test_contract_reports_private_public_key_order_with_actual_expected_and_line(tmp_path) -> None:
    """模板正确而私有公共键错序时，也必须输出脱敏的键名和行号。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    private_lines = _synthetic_private_content(example_content).splitlines()
    first_index = next(
        index for index, line in enumerate(private_lines) if line.startswith("PLATFORM_BIND_HOST=")
    )
    second_index = next(
        index for index, line in enumerate(private_lines) if line.startswith("PLATFORM_PUBLIC_HOST=")
    )
    private_lines[first_index], private_lines[second_index] = (
        private_lines[second_index],
        private_lines[first_index],
    )
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(example_content, encoding="utf-8")
    private.write_text("\n".join(private_lines) + "\n", encoding="utf-8")

    issues = validate_contract(private, example)

    assert issues == (
        f"env:order:actual:PLATFORM_PUBLIC_HOST@line:{first_index + 1}:"
        "expected:PLATFORM_BIND_HOST",
    )


def test_contract_streams_files_without_whole_file_read_text(tmp_path, monkeypatch) -> None:
    """生产校验路径必须逐行脱敏解析，不能把私有文件全文驻留在局部变量。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(example_content, encoding="utf-8")
    private.write_text(_synthetic_private_content(example_content), encoding="utf-8")

    def reject_whole_file_read(*args, **kwargs):
        raise AssertionError("validate_contract must not call Path.read_text")

    monkeypatch.setattr(Path, "read_text", reject_whole_file_read)

    assert validate_contract(private, example) == ()


@pytest.mark.parametrize(
    ("failed_name", "expected_issue"),
    [
        (".env", "read_error:.env"),
        (".env.example", "read_error:.env.example"),
    ],
)
def test_contract_redacts_file_read_errors(tmp_path, monkeypatch, failed_name, expected_issue) -> None:
    """配置文件读取失败只能报告文件类型，不能传播底层异常或配置值。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text(example_content, encoding="utf-8")
    private.write_text(_synthetic_private_content(example_content), encoding="utf-8")
    failed_path = tmp_path / failed_name
    original_open = Path.open

    def fail_selected_path(self, *args, **kwargs):
        if self == failed_path:
            raise PermissionError("synthetic-secret-must-not-escape")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_selected_path)

    issues = validate_contract(private, example)

    assert issues == (expected_issue,)
    assert "synthetic-secret-must-not-escape" not in "\n".join(issues)


@pytest.mark.parametrize("position", ["middle", "tail"])
def test_contract_reports_duplicate_template_key_without_values(tmp_path, position) -> None:
    """模板中部或尾部重复键都必须返回稳定的键名与行号诊断。"""
    example_content = _read(ENV_EXAMPLE_FILE)
    lines = example_content.splitlines()
    source_index = next(
        index for index, line in enumerate(lines) if line.startswith("PLATFORM_BIND_HOST=")
    )
    duplicate_line = lines[source_index]
    if position == "middle":
        lines.insert(source_index + 1, duplicate_line)
    else:
        lines.append(duplicate_line)
    duplicate_line_number = (
        source_index + 2 if position == "middle" else len(lines)
    )
    example = tmp_path / ".env.example"
    private = tmp_path / ".env"
    example.write_text("\n".join(lines) + "\n", encoding="utf-8")
    private.write_text(_synthetic_private_content(example_content), encoding="utf-8")

    issues = validate_contract(private, example)

    expected = (
        "duplicate:.env.example:PLATFORM_BIND_HOST@line:"
        f"{source_index + 1},{duplicate_line_number}"
    )
    assert expected in issues
    assert duplicate_line.split("=", 1)[1] not in "\n".join(issues)


def test_fixed_jenkins_contract_is_not_read_from_retired_environment_keys() -> None:
    """固定 Job、容量、本地 workspace 和删除策略不能继续由根 env 覆盖。"""
    sources = {
        relative: _read(ROOT / relative)
        for relative in (
            "jenkins/scripts/configure-local-mounted-jobs.groovy",
            "jenkins/scripts/configure-executors.groovy",
            "jenkins/scripts/platform_bootstrap/jenkins_api.py",
        )
    }
    combined = "\n".join(sources.values())
    for key in (
        "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME",
        "JENKINS_EXECUTORS",
        "AIAPITEST_LOCAL_WORKSPACE",
        "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS",
        "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED",
        "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES",
    ):
        assert f"getenv('{key}')" not in combined
        assert f'getenv("{key}")' not in combined
        assert f'get("{key}")' not in combined
    assert "legacyDailyJob.delete()" not in sources[
        "jenkins/scripts/configure-local-mounted-jobs.groovy"
    ]
    assert "AiApiTest-DWP-Platform-Bootstrap" in sources[
        "jenkins/scripts/platform_bootstrap/jenkins_api.py"
    ]


def test_local_job_init_cannot_be_disabled_by_removed_root_option() -> None:
    """Compose 本地 Jenkins 必须无条件进入受管 Job 的幂等修复逻辑。"""
    init_script = _read(ROOT / "jenkins/scripts/configure-local-mounted-jobs.groovy")

    assert "LOCAL_WORKSPACE_REPO is not true" not in init_script
    assert "System.getenv('LOCAL_WORKSPACE_REPO')" not in init_script
    assert "/workspace/AiApiTest-DWP" in init_script


def test_deploy_helpers_stop_after_creating_public_only_env_and_use_new_address_keys() -> None:
    """首次复制模板后必须等待人工补私有区，地址提示只读取新公共基础量。"""
    helpers = {
        relative: _read(ROOT / relative)
        for relative in ("scripts/deploy-docker.ps1", "scripts/deploy-docker.sh")
    }
    for source in helpers.values():
        create_index = source.index(".env.example")
        start_index = source.index("docker compose up")
        between = source[create_index:start_index]
        assert "exit" in between.lower() or "return" in between.lower()
        for key in (
            "PLATFORM_PUBLIC_HOST",
            "PLATFORM_PUBLIC_SCHEME",
            "JENKINS_HTTP_PORT",
            "MYSQL_HOST_PORT",
        ):
            assert key in source
        for retired in ("JENKINS_PUBLIC_BASE_URL", "MYSQL_BIND_HOST"):
            assert retired not in source
    assert "ConvertFrom-DotEnvValue" in helpers["scripts/deploy-docker.ps1"]
    assert "Format-HostPortHost" in helpers["scripts/deploy-docker.ps1"]
    assert "dotenv_value" in helpers["scripts/deploy-docker.sh"]
    assert "format_host_port_host" in helpers["scripts/deploy-docker.sh"]


def test_trigger_configuration_hint_does_not_restore_retired_options() -> None:
    """配置错误提示只能指导公共地址基础量和私有 Jenkins 凭据。"""
    cli = _read(ROOT / "jenkins/scripts/platform_bootstrap/cli.py")

    assert "Jenkins URL, Job, username, token, and timeout keys" not in cli
    for key in (
        "PLATFORM_PUBLIC_HOST",
        "PLATFORM_PUBLIC_SCHEME",
        "JENKINS_HTTP_PORT",
        "JENKINS_USERNAME",
        "JENKINS_API_TOKEN",
    ):
        assert key in cli
