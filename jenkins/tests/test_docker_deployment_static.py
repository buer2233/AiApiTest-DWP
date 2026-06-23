from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def test_docker_compose_defines_mysql_and_jenkins_services():
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
    content = (ROOT_DIR / "docker-compose.yml").read_text(encoding="utf-8")

    assert "${MYSQL_BIND_HOST:-127.0.0.1}:${MYSQL_HOST_PORT:-3307}:3306" in content
    assert "${JENKINS_HTTP_PORT:-8080}:8080" in content
    assert "${JENKINS_AGENT_PORT:-50001}:50000" in content
    assert "MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:?Set MYSQL_ROOT_PASSWORD in .env}" in content
    assert "MYSQL_ALLOW_EMPTY_PASSWORD" not in content


def test_env_example_documents_required_values_without_real_secrets():
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
    content = (ROOT_DIR / ".gitignore").read_text(encoding="utf-8")

    assert "\n.env\n" in f"\n{content}\n"


def test_one_click_scripts_start_compose_services():
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
    override_file = ROOT_DIR / "docker-compose.jenkins-tools.yml"

    assert override_file.exists()

    content = override_file.read_text(encoding="utf-8")
    assert "context: ." in content
    assert "dockerfile: docker/jenkins/Dockerfile" in content
    assert "aiapitest-jenkins:lts-jdk17-tools" in content


def test_jenkins_image_installs_pipeline_runtime_tools():
    dockerfile = ROOT_DIR / "docker" / "jenkins" / "Dockerfile"

    assert dockerfile.exists()

    content = dockerfile.read_text(encoding="utf-8")
    assert "FROM jenkins/jenkins:lts-jdk17" in content
    assert "python3" in content
    assert "python3-venv" in content
    assert "git" in content
    assert "allure-commandline" in content
