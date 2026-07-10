"""Docker 部署配置静态测试。

本文件直接读取 Compose、环境模板、一键部署脚本和 Jenkins 工具链 Dockerfile，
验证 Docker 快速部署的服务、端口、安全默认值和工具链约束。
"""

from pathlib import Path
import shutil
import subprocess

import pytest


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_docker_compose_defines_mysql_and_jenkins_services():
    """默认 Compose 必须定义 MySQL 和 Jenkins，并挂载持久化数据卷。"""
    compose_file = ROOT_DIR / "docker-compose.yml"

    assert compose_file.exists()

    content = compose_file.read_text(encoding="utf-8")
    assert "mysql:" in content
    assert "jenkins:" in content
    assert "mysql:8.4" in content
    assert "jenkins/jenkins:lts-jdk17" in content
    assert "aiapitest-mysql-data:/var/lib/mysql" in content
    assert "aiapitest-jenkins-home:/var/jenkins_home" in content
    assert "${PROJECT_WORKSPACE:-.}:/workspace/AiApiTest-DWP" in content


def test_docker_compose_uses_env_driven_ports_and_safe_defaults():
    """Compose 端口和密码必须由环境变量驱动，且不能允许空 MySQL 密码。"""
    content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert "${MYSQL_BIND_HOST:-127.0.0.1}:${MYSQL_HOST_PORT:-3307}:3306" in content
    assert "${JENKINS_HTTP_PORT:-8080}:8080" in content
    assert "${JENKINS_AGENT_PORT:-50001}:50000" in content
    assert "MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD in .env}" in content
    assert "MYSQL_ALLOW_EMPTY_PASSWORD" not in content


def test_docker_compose_injects_jenkins_runtime_env_from_root_env():
    """Jenkins 容器必须显式接收根 .env 中声明的 Pipeline 默认变量。"""
    content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    for variable in [
        "JENKINS_PUBLIC_BASE_URL: ${JENKINS_PUBLIC_BASE_URL:-http://localhost:8080}",
        "JENKINS_FAILED_RERUN_JOB_NAME: ${JENKINS_FAILED_RERUN_JOB_NAME:-AiApiTest-DWP-Failed-Rerun}",
        "JENKINS_MODULE_RERUN_JOB_NAME: ${JENKINS_MODULE_RERUN_JOB_NAME:-AiApiTest-DWP-Module-Rerun}",
        "JENKINS_DAILY_FULL_JOB_PREFIX: ${JENKINS_DAILY_FULL_JOB_PREFIX:-AiApiTest-DWP-Daily-Full-Module}",
        "JENKINS_DEFAULT_CASE_PATH: ${JENKINS_DEFAULT_CASE_PATH:-test_case/test_gbif_case}",
        "JENKINS_API_TEST_DIR: ${JENKINS_API_TEST_DIR:-api-test}",
        "JENKINS_PYTHON_VENV_DIR: ${JENKINS_PYTHON_VENV_DIR:-.venv}",
        "LOCAL_WORKSPACE_REPO: ${LOCAL_WORKSPACE_REPO:-true}",
        "AIAPITEST_LOCAL_WORKSPACE: ${AIAPITEST_LOCAL_WORKSPACE:-/workspace/AiApiTest-DWP}",
        "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS: ${AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS:-false}",
        "CI_RUN_RETENTION_DAYS: ${CI_RUN_RETENTION_DAYS:-30}",
    ]:
        assert variable in content


def test_env_example_documents_required_values_without_real_secrets():
    """环境模板只保留通用网络配置，账号、密码、密钥和固定默认值不进入模板。"""
    env_file = ROOT_DIR / ".env.example"

    assert env_file.exists()

    content = env_file.read_text(encoding="utf-8")
    for variable in [
        "MYSQL_BIND_HOST=127.0.0.1",
        "MYSQL_HOST_PORT=3307",
        "MYSQL_HOST=127.0.0.1",
        "JENKINS_HTTP_PORT=8080",
        "JENKINS_AGENT_PORT=50001",
        "JENKINS_PUBLIC_BASE_URL=http://localhost:8080",
        "LOCAL_WORKSPACE_REPO=true",
        "AIAPITEST_LOCAL_WORKSPACE=/workspace/AiApiTest-DWP",
        "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS=false",
        "PROJECT_WORKSPACE=.",
        "CI_RUN_RETENTION_DAYS=30",
        "BACKEND_SERVICE_URL=http://127.0.0.1:8000",
        "BACKEND_API_BASE_URL=http://127.0.0.1:8000/api/v1",
        "FRONTEND_SERVICE_URL=http://127.0.0.1:5173",
        "FRONTEND_DEV_HOST=127.0.0.1",
        "FRONTEND_DEV_PORT=5173",
        "FRONTEND_DEV_API_PROXY_TARGET=http://127.0.0.1:8000",
        "VITE_API_BASE_URL=/api/v1",
        "VITE_API_TIMEOUT_MS=10000",
        "PLAYWRIGHT_WEB_SERVER_HOST=127.0.0.1",
        "PLAYWRIGHT_WEB_SERVER_PORT=4173",
        "PLAYWRIGHT_BASE_URL=http://127.0.0.1:4173",
    ]:
        assert variable in content
    for forbidden_variable in [
        "MYSQL_DATABASE=",
        "MYSQL_ROOT_PASSWORD=",
        "MYSQL_PASSWORD=",
        "JENKINS_USERNAME=",
        "JENKINS_API_TOKEN=",
        "DJANGO_SETTINGS_MODULE=",
        "DJANGO_SECRET_KEY=",
        "DJANGO_DEBUG=",
        "DJANGO_ALLOWED_HOSTS=",
        "DB_ENGINE=",
        "DB_CONN_MAX_AGE=",
        "AUTH_COOKIE_NAME=",
        "AUTH_COOKIE_MAX_AGE_SECONDS=",
        "AUTH_COOKIE_SECURE=",
        "AUTH_COOKIE_SAMESITE=",
        "AUTH_COOKIE_PATH=",
        "AUTH_TOKEN_SECRET=",
        "AUTH_TOKEN_ISSUER=",
        "INITIAL_ADMIN_USERNAME=",
        "INITIAL_ADMIN_DISPLAY_NAME=",
        "INITIAL_ADMIN_PASSWORD=",
        "JENKINS_DEFAULT_CASE_PATH=",
        "JENKINS_API_TEST_DIR=",
        "JENKINS_PYTHON_VENV_DIR=",
        "JENKINS_OPTS=",
        "FRONTEND_SERVICE_NAME=",
        "BACKEND_SERVICE_NAME=",
        "TZ=",
    ]:
        assert forbidden_variable not in content
    for forbidden_secret in ["admin123456", "change-me-", "eyJ", "ghp_", "sk-", "xoxb-"]:
        assert forbidden_secret not in content


def test_local_env_file_is_git_ignored():
    """本地 .env 必须被 git 忽略，避免私有密码进入仓库。"""
    content = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")

    assert "\n.env\n" in f"\n{content}\n"


def test_runtime_temp_directory_is_git_ignored():
    """本地调试脚本和运行日志目录不得被误提交。"""
    content = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")

    assert "\n.tmp/\n" in f"\n{content}\n"


def test_one_click_scripts_start_compose_services():
    """PowerShell 和 Bash 一键脚本都必须复制 env 模板并启动核心服务。"""
    powershell_script = ROOT_DIR / "scripts" / "deploy-docker.ps1"
    bash_script = ROOT_DIR / "scripts" / "deploy-docker.sh"

    assert powershell_script.exists()
    assert bash_script.exists()

    ps_content = powershell_script.read_text(encoding="utf-8")
    sh_content = bash_script.read_text(encoding="utf-8")

    assert "Copy-Item" in ps_content
    assert "docker compose up -d mysql jenkins" in ps_content
    assert "cp .env.example .env" in sh_content
    assert "docker compose up -d mysql jenkins" in sh_content
    assert "JENKINS_PUBLIC_BASE_URL" in ps_content
    assert "JENKINS_PUBLIC_BASE_URL" in sh_content
    assert "MYSQL_BIND_HOST" in ps_content
    assert "MYSQL_BIND_HOST" in sh_content


def test_one_click_scripts_inject_local_jenkins_api_credentials_to_private_env():
    """本地 Jenkins API token 只能写入私有 .env，避免后端重启后再次匿名触发失败。"""
    powershell_script = ROOT_DIR / "scripts" / "deploy-docker.ps1"
    bash_script = ROOT_DIR / "scripts" / "deploy-docker.sh"

    ps_content = powershell_script.read_text(encoding="utf-8")
    sh_content = bash_script.read_text(encoding="utf-8")

    for content in [ps_content, sh_content]:
        assert "aiapitest-local-api-token.txt" in content
        assert "JENKINS_USERNAME" in content
        assert "JENKINS_API_TOKEN" in content
        assert ".env" in content

    assert "Write-Host $jenkinsApiToken" not in ps_content
    assert 'echo "$JENKINS_API_TOKEN"' not in sh_content


def test_default_compose_bootstraps_local_jenkins_api_token_on_clean_volume():
    """默认 Compose 必须把受版本控制的 token 初始化脚本带入干净 Jenkins 数据卷。"""
    compose_content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    init_script = ROOT_DIR / "jenkins" / "scripts" / "99-aiapitest-local-api-token.groovy"

    assert init_script.exists()
    assert (
        "./jenkins/scripts/99-aiapitest-local-api-token.groovy:"
        "/var/jenkins_home/init.groovy.d/99-aiapitest-local-api-token.groovy:ro"
    ) in compose_content

    script_content = init_script.read_text(encoding="utf-8")
    assert "generateNewToken" in script_content
    assert "/var/jenkins_home/aiapitest-local-api-token.txt" in script_content
    assert "plainValue" in script_content
    assert "setSecurityRealm" not in script_content
    assert "new HudsonPrivateSecurityRealm" not in script_content
    assert "findMatchingToken" in script_content
    assert "getTokenListSortedByName" in script_content
    assert "revokeToken" in script_content
    assert "ATOMIC_MOVE" in script_content
    assert 'PosixFilePermissions.fromString("rw-------")' in script_content


def test_powershell_private_env_writer_uses_utf8_without_bom():
    """Windows PowerShell 5.1 重写 .env 时不得给首个键添加 UTF-8 BOM。"""
    content = (ROOT_DIR / "scripts" / "deploy-docker.ps1").read_text(encoding="utf-8")

    assert "New-Object System.Text.UTF8Encoding($false)" in content
    assert "[System.IO.File]::WriteAllLines" in content
    assert "Set-Content -LiteralPath $Path" not in content


def test_powershell_deploy_script_is_parseable_by_windows_powershell():
    """Windows PowerShell 5.1 必须能解析脚本，避免 UTF-8 注释被误判为语法。"""
    if not shutil.which("powershell.exe"):
        pytest.skip("powershell.exe is not available on this platform")

    script = ROOT_DIR / "scripts" / "deploy-docker.ps1"
    command = (
        "$tokens=$null; $errors=$null; "
        f"[System.Management.Automation.Language.Parser]::ParseFile('{script}', [ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count -gt 0) { $errors | ForEach-Object { $_.Message }; exit 1 }"
    )

    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def test_optional_jenkins_tools_override_builds_custom_image():
    """可选 override 必须构建带测试工具链的 Jenkins 镜像。"""
    override_file = ROOT_DIR / "docker-compose.jenkins-tools.yml"

    assert override_file.exists()

    content = override_file.read_text(encoding="utf-8")
    assert "context: ." in content
    assert "dockerfile: docker/jenkins/Dockerfile" in content
    assert "aiapitest-jenkins:lts-jdk17-tools" in content


def test_jenkins_image_installs_pipeline_runtime_tools():
    """Jenkins 工具链镜像必须安装 Python、git 和 Allure CLI。"""
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"

    assert dockerfile.exists()

    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM jenkins/jenkins:lts-jdk17" in content
    assert "python3" in content
    assert "python3-venv" in content
    assert "python-is-python3" in content
    assert "git" in content
    assert "allure-commandline" in content


def test_jenkins_tools_image_installs_allure_jenkins_plugin():
    """Jenkins 工具链镜像必须预装 Allure 插件，才能在 Jenkins 内展示报告。"""
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"

    content = dockerfile.read_text(encoding="utf-8")

    assert "jenkins-plugin-cli" in content
    assert "allure-jenkins-plugin" in content
    assert "ALLURE_COMMANDLINE_HOME" in content
    assert "configure-allure-commandline.groovy" in content


def test_jenkins_tools_image_allows_workspace_tmp_directory_creation():
    """Jenkins 用户必须能在 /workspace 下创建 @tmp 控制目录。"""
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"

    content = dockerfile.read_text(encoding="utf-8")

    assert "mkdir -p /workspace" in content
    assert "chown jenkins:jenkins /workspace" in content


def test_allure_commandline_init_script_registers_installed_cli():
    """工具链镜像的 init 脚本必须注册本机已安装的 Allure CLI。"""
    script = ROOT_DIR / "jenkins" / "scripts" / "configure-allure-commandline.groovy"

    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "AllureCommandlineInstallation" in content
    assert "ALLURE_COMMANDLINE_HOME" in content
    assert "Allure Commandline" in content
    assert "setInstallations" in content
