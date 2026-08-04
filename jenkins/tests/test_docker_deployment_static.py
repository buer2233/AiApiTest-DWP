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
    """Compose 端口统一绑定平台地址，且不能允许空 MySQL 密码。"""
    content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert content.count("host_ip: ${PLATFORM_BIND_HOST:-127.0.0.1}") == 5
    assert 'published: "${MYSQL_HOST_PORT:-3307}"' in content
    assert 'published: "${JENKINS_HTTP_PORT:-8080}"' in content
    assert 'published: "${JENKINS_AGENT_PORT:-50001}"' in content
    assert "MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD in .env}" in content
    assert "MYSQL_ALLOW_EMPTY_PASSWORD" not in content


def test_docker_compose_injects_only_necessary_jenkins_runtime_configuration():
    """Jenkins 只接收私有同步配置和必要调优项，固定协议不得继续插值。"""
    content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    for variable in [
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL: ${JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL:-}",
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH: ${JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH:-main}",
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID: ${JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID:-}",
        "JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID: ${JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID:-}",
        "JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID: ${JENKINS_ENVIRONMENT_CATALOG_SYNC_PUSH_CREDENTIALS_ID:-}",
        "FRONTEND_PLAYWRIGHT_BASE_IMAGE: ${FRONTEND_PLAYWRIGHT_BASE_IMAGE:-mcr.m.daocloud.io/playwright:v1.61.1-noble}",
        "CI_RUN_RETENTION_DAYS: ${CI_RUN_RETENTION_DAYS:-30}",
    ]:
        assert variable in content
    for retired in [
        "JENKINS_PUBLIC_BASE_URL:",
        "JENKINS_GENERIC_PIPELINE_JOB_NAME:",
        "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME:",
        "JENKINS_EXECUTORS:",
        "LOCAL_WORKSPACE_REPO:",
        "AIAPITEST_LOCAL_WORKSPACE:",
        "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED:",
        "JENKINS_STAGE13_LEGACY_DAILY_JOB_NAMES:",
    ]:
        assert retired not in content


def test_env_example_documents_required_values_without_real_secrets():
    """环境模板只保留通用网络配置，账号、密码、密钥和固定默认值不进入模板。"""
    env_file = ROOT_DIR / ".env.example"

    assert env_file.exists()

    content = env_file.read_text(encoding="utf-8")
    for variable in [
        "PLATFORM_BIND_HOST=127.0.0.1",
        "PLATFORM_PUBLIC_HOST=127.0.0.1",
        "PLATFORM_PUBLIC_SCHEME=http",
        "MYSQL_HOST_PORT=3307",
        "JENKINS_HTTP_PORT=8080",
        "JENKINS_AGENT_PORT=50001",
        "BACKEND_HOST_PORT=8000",
        "FRONTEND_HOST_PORT=5173",
        "PROJECT_WORKSPACE=.",
        "DOCKER_GID=0",
        "CI_RUN_RETENTION_DAYS=30",
        "FRONTEND_PLAYWRIGHT_BASE_IMAGE=mcr.m.daocloud.io/playwright:v1.61.1-noble",
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


def test_compose_configures_forty_jenkins_executors_via_init_script():
    """Compose Jenkins 应通过 init Groovy 将 controller executors 固定为 40。"""
    compose = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    init_script_path = ROOT_DIR / "jenkins" / "scripts" / "configure-executors.groovy"

    assert "JENKINS_EXECUTORS:" not in compose
    assert "configure-executors.groovy:/var/jenkins_home/init.groovy.d/20-aiapitest-executors.groovy:ro" in compose
    assert init_script_path.exists()
    script = init_script_path.read_text(encoding="utf-8")
    assert "def executorCount = 40" in script
    assert "System.getenv" not in script
    assert "setNumExecutors" in script
    assert "jenkins.save()" in script


def test_compose_bootstraps_stage13_jobs_via_versioned_init_script():
    """Compose 启动必须自动创建唯一 Daily、Worker 和目录同步 Job。"""
    compose = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert (
        "./jenkins/scripts/configure-local-mounted-jobs.groovy:"
        "/var/jenkins_home/init.groovy.d/30-aiapitest-local-jobs.groovy:ro"
    ) in compose


def test_compose_retires_only_the_exact_legacy_local_jobs_init_file():
    """版本化迁移只能删除指定历史 init 文件，且不得跟随符号链接或广泛删除。"""
    compose = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    script_path = ROOT_DIR / "jenkins" / "scripts" / "25-aiapitest-retire-legacy-local-jobs.groovy"

    assert (
        "./jenkins/scripts/25-aiapitest-retire-legacy-local-jobs.groovy:"
        "/var/jenkins_home/init.groovy.d/25-aiapitest-retire-legacy-local-jobs.groovy:ro"
    ) in compose
    assert script_path.exists()

    script = script_path.read_text(encoding="utf-8")
    assert "/var/jenkins_home/init.groovy.d/configure-local-mounted-jobs.groovy" in script
    assert "Files.deleteIfExists" in script
    assert "Files.isRegularFile" in script
    assert "LinkOption.NOFOLLOW_LINKS" in script
    assert "Files.isSymbolicLink" in script

    for forbidden_api in [
        "Files.delete(",
        "Files.walk(",
        "Files.find(",
        "Files.list(",
        "FileUtils.delete",
        "deleteDir(",
        "deleteRecursively(",
        "eachFileRecurse",
    ]:
        assert forbidden_api not in script


def test_platform_bootstrap_job_name_is_fixed_in_jenkins_init_script():
    """环境 Job 使用冻结名称，Compose 不得再提供改名旁路。"""
    compose = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")
    init_script = (ROOT_DIR / "jenkins" / "scripts" / "configure-local-mounted-jobs.groovy").read_text(
        encoding="utf-8"
    )

    assert "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME:" not in compose
    assert "def platformBootstrapJobName = 'AiApiTest-DWP-Platform-Bootstrap'" in init_script


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
    for public_key in ["PLATFORM_PUBLIC_HOST", "PLATFORM_PUBLIC_SCHEME", "JENKINS_HTTP_PORT", "MYSQL_HOST_PORT"]:
        assert public_key in ps_content
        assert public_key in sh_content


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


def test_jenkins_image_installs_pipeline_control_tools():
    """Jenkins 工具链镜像必须安装 Docker/Compose、轻量 Python、git 和 Allure CLI。"""
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"

    assert dockerfile.exists()

    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM jenkins/jenkins:lts-jdk17" in content
    assert "python3" in content
    assert "python-is-python3" in content
    assert "git" in content
    assert "docker-ce-cli" in content
    assert "docker-buildx-plugin" in content
    assert "docker-compose-plugin" in content
    assert "allure-commandline" in content
    assert "python3-venv" not in content


def test_api_test_requirements_only_exist_in_api_runner_image():
    """controller 不预装业务依赖，api-runner 是唯一 pytest/Allure 运行环境。"""
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    runner_content = (ROOT_DIR / "api-test" / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY api-test/requirements.txt" not in content
    assert "AIAPITEST_PREINSTALLED_REQUIREMENTS" not in content
    assert "python3-venv" not in content
    assert "COPY api-test/requirements.txt" in runner_content
    assert "python -m pip install" in runner_content
    assert "api-test-requirements.txt" in runner_content


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
