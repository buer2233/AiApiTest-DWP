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


def test_env_example_documents_required_values_without_real_secrets():
    """环境模板只能包含占位值，不能写入真实账号、密码或 token。"""
    env_file = ROOT_DIR / ".env.example"

    assert env_file.exists()

    content = env_file.read_text(encoding="utf-8")
    assert "MYSQL_ROOT_PASSWORD=change-me-local-root-password" in content
    assert "MYSQL_PASSWORD=change-me-local-root-password" in content
    assert "MYSQL_DATABASE=ai_api_test_platform" in content
    assert "JENKINS_HTTP_PORT=8080" in content
    assert "JENKINS_AGENT_PORT=50001" in content
    assert "admin123456" not in content
    assert "token" not in content.lower()


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
