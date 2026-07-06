"""Docker 部署配置静态测试。

本文件直接读取 Compose、环境模板、一键部署脚本和 Jenkins 工具链 Dockerfile，
验证 Docker 快速部署的服务、端口、安全默认值和工具链约束。
"""

from pathlib import Path


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
        "JENKINS_DEFAULT_CASE_PATH: ${JENKINS_DEFAULT_CASE_PATH:-test_case/test_gbif_case}",
        "JENKINS_API_TEST_DIR: ${JENKINS_API_TEST_DIR:-api-test}",
        "JENKINS_PYTHON_VENV_DIR: ${JENKINS_PYTHON_VENV_DIR:-.venv}",
        "LOCAL_WORKSPACE_REPO: ${LOCAL_WORKSPACE_REPO:-true}",
        "AIAPITEST_LOCAL_WORKSPACE: ${AIAPITEST_LOCAL_WORKSPACE:-/workspace/AiApiTest-DWP}",
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
        "PROJECT_WORKSPACE=.",
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
    assert "git" in content
    assert "allure-commandline" in content
