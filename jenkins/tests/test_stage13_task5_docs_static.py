"""Stage13 Task 5 环境模板、文档与 AI 唯一入口静态门禁。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AGENT_RULES = [
    ROOT / "AGENTS.md",
    ROOT / "jenkins" / "AGENTS.md",
    ROOT / "docker" / "AGENTS.md",
    ROOT / "back-end" / "AGENTS.md",
    ROOT / "front-end" / "AGENTS.md",
    ROOT / "api-test" / "AGENTS.md",
]

EXPECTED_ENV = {
    "MYSQL_BIND_HOST": "127.0.0.1",
    "MYSQL_HOST_PORT": "3307",
    "MYSQL_HOST": "127.0.0.1",
    "JENKINS_HTTP_PORT": "8080",
    "JENKINS_AGENT_PORT": "50001",
    "JENKINS_EXECUTORS": "40",
    "JENKINS_PUBLIC_BASE_URL": "http://localhost:8080",
    "JENKINS_GENERIC_PIPELINE_JOB_NAME": "AiApiTest-DWP-Pipeline",
    "JENKINS_API_BASE_URL": "http://127.0.0.1:8080",
    "JENKINS_FAILED_RERUN_JOB_NAME": "AiApiTest-DWP-Failed-Rerun",
    "JENKINS_MODULE_RERUN_JOB_NAME": "AiApiTest-DWP-Module-Rerun",
    "JENKINS_DAILY_FULL_JOB_PREFIX": "AiApiTest-DWP-Daily-Full-Module",
    "JENKINS_DAILY_FULL_JOB_NAME": "AiApiTest-DWP-Daily-Full-Module",
    "JENKINS_DAILY_FULL_WORKER_JOB_NAME": "AiApiTest-DWP-Daily-Full-Module-Worker",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_JOB_NAME": "AiApiTest-DWP-Environment-Catalog-Sync",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_URL": "",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_BRANCH": "main",
    "JENKINS_ENVIRONMENT_CATALOG_SYNC_SCM_CREDENTIALS_ID": "",
    "JENKINS_ENVIRONMENT_CATALOG_SERVICE_CREDENTIALS_ID": "",
    "JENKINS_STAGE13_LEGACY_DAILY_REMOVAL_APPROVED": "false",
    "JENKINS_PLATFORM_BOOTSTRAP_JOB_NAME": "AiApiTest-DWP-Platform-Bootstrap",
    "JENKINS_REQUEST_TIMEOUT_SECONDS": "15",
    "JENKINS_QUEUE_POLL_INTERVAL_SECONDS": "5",
    "JENKINS_BUILD_POLL_INTERVAL_SECONDS": "10",
    "JENKINS_BUILD_POLL_TIMEOUT_SECONDS": "1800",
    "JENKINS_SYNC_HEARTBEAT_MAX_AGE_SECONDS": "60",
    "LOCAL_WORKSPACE_REPO": "true",
    "AIAPITEST_LOCAL_WORKSPACE": "/workspace/AiApiTest-DWP",
    "AIAPITEST_REPLACE_EXISTING_LOCAL_JOBS": "false",
    "PROJECT_WORKSPACE": ".",
    "CI_RUN_RETENTION_DAYS": "30",
    "DOCKER_GID": "0",
    "BACKEND_BIND_HOST": "127.0.0.1",
    "BACKEND_HOST_PORT": "8000",
    "BACKEND_SERVICE_URL": "http://127.0.0.1:8000",
    "BACKEND_API_BASE_URL": "http://127.0.0.1:8000/api/v1",
    "FRONTEND_BIND_HOST": "127.0.0.1",
    "FRONTEND_HOST_PORT": "5173",
    "FRONTEND_SERVICE_URL": "http://127.0.0.1:5173",
    "FRONTEND_DEV_HOST": "127.0.0.1",
    "FRONTEND_DEV_PORT": "5173",
    "FRONTEND_DEV_API_PROXY_TARGET": "http://127.0.0.1:8000",
    "FRONTEND_PLAYWRIGHT_BASE_IMAGE": "mcr.m.daocloud.io/playwright:v1.61.1-noble",
    "VITE_API_BASE_URL": "/api/v1",
    "VITE_API_TIMEOUT_MS": "10000",
    "PLAYWRIGHT_WEB_SERVER_HOST": "127.0.0.1",
    "PLAYWRIGHT_WEB_SERVER_PORT": "4173",
    "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:4173",
}


def read_text(relative_path: str) -> str:
    """读取仓库文件，失败时给出可定位的相对路径。"""
    path = ROOT / relative_path
    assert path.is_file(), f"missing required Task5 file: {relative_path}"
    return path.read_text(encoding="utf-8")


def parse_env_template(content: str) -> dict[str, str]:
    """只解析模板中非注释的 key=value 行，避免把说明文字计入变量集合。"""
    values: dict[str, str] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def test_env_example_has_exactly_the_public_task5_variable_contract():
    """模板必须恰有 48 项非敏感公开配置，新增项与真实消费者保持一致。"""
    variables = parse_env_template(read_text(".env.example"))

    assert variables == EXPECTED_ENV
    assert len(variables) == 48


def test_env_example_does_not_publish_private_or_build_metadata_values():
    """凭据、数据库私有项及 Pipeline 临时 hash 不能进入可提交模板。"""
    content = read_text(".env.example")
    for forbidden in [
        "MYSQL_DATABASE=",
        "MYSQL_ROOT_PASSWORD=",
        "MYSQL_PASSWORD=",
        "JENKINS_USERNAME=",
        "JENKINS_API_TOKEN=",
        "DJANGO_SECRET_KEY=",
        "AUTH_TOKEN_SECRET=",
        "AIAPITEST_SOURCE_REVISION=",
        "BACKEND_BUILD_HASH=",
        "FRONTEND_BUILD_HASH=",
        "API_RUNNER_BUILD_HASH=",
    ]:
        assert forbidden not in content


def test_all_agent_rules_require_the_same_ai_only_platform_environment_entrypoint():
    """根和五个模块规则必须同步禁止 AI 绕开固定环境 Job。"""
    required_markers = [
        "平台环境唯一入口",
        "scripts/trigger-platform-bootstrap.ps1",
        "scripts/trigger-platform-bootstrap.sh",
        "AI 禁止直接执行",
        "docker compose up/restart/stop/down",
        "docker build",
        "pip install",
        "npm install/npm ci",
        "runserver",
        "Vite",
        "MySQL 与 Jenkins",
        "主人/平台运维",
        "幂等创建或修复",
        "重新构建",
    ]

    for path in AGENT_RULES:
        content = path.read_text(encoding="utf-8")
        missing = [marker for marker in required_markers if marker not in content]
        assert not missing, f"{path.relative_to(ROOT)} missing Task5 AI rule markers: {missing}"


def test_quick_start_documents_keep_bootstrap_commands_outside_ai_execution():
    """部署文档只能授权主人或平台运维启动 MySQL/Jenkins 基础容器。"""
    deployment = read_text("docker/DEPLOYMENT.md")

    assert "仅主人/平台运维执行，AI 不得执行" in deployment
    assert "docker compose up -d mysql jenkins" in deployment
    assert "环境 Job/helper 永不管理 MySQL 与 Jenkins" in deployment
    assert "## AI 部署" not in deployment
    assert "AI 自动部署" not in deployment


def test_jenkins_readme_documents_auto_created_environment_job_and_safe_contract():
    """环境 Job 必须由 Jenkins init 幂等创建/修复，并说明固定安全契约。"""
    content = read_text("jenkins/README.md")
    for marker in [
        "AiApiTest-DWP-Platform-Bootstrap",
        "jenkins/Jenkinsfile.platform-bootstrap",
        "build_all=true",
        "run_full_tests=false",
        "disableConcurrentBuilds",
        "LOCAL_WORKSPACE_REPO",
        "checkout scm",
        "DOCKER_GID",
        "受信任",
        "不受信任 SCM/PR Job",
        "三域",
        "一次安装",
        "不执行 migration",
        "不执行 rollback",
        "不删除 volume",
        "Jenkins Allure 插件",
        "Jenkins 启动时幂等创建或修复",
        "重新构建",
    ]:
        assert marker in content
    assert "手工创建该 Job" not in content


def test_root_readme_and_deployment_document_automatic_environment_job_creation():
    """用户只 bootstrap 基础容器；环境 Job 由版本化 init 脚本自动提供。"""
    readme = read_text("README.md")
    deployment = read_text("docker/DEPLOYMENT.md")

    for content in [readme, deployment]:
        assert "Jenkins 启动时幂等创建或修复" in content
        assert "手工创建固定环境 Job" not in content
        assert "手工创建一个 Pipeline Job" not in content


def test_deployment_and_autonomous_docs_state_socket_risk_and_ai_diagnostic_boundary():
    """Socket 仅限受信任本地环境，AI 失败时只能回到 Jenkins 诊断与重建。"""
    deployment = read_text("docker/DEPLOYMENT.md")
    autonomous = read_text("docs/自主开发流水线.md")
    combined = deployment + "\n" + autonomous

    for marker in [
        "主机级 Docker 控制能力",
        "不是生产部署安全承诺",
        "chmod 666 /var/run/docker.sock",
        "Jenkins 结构化诊断",
        "修复后重新构建",
        "环境 Job",
        "scripts/trigger-platform-bootstrap.ps1",
        "scripts/trigger-platform-bootstrap.sh",
    ]:
        assert marker in combined


def test_task5_requirement_documents_the_actual_eight_new_public_variables():
    """受版本控制的需求资料必须与公开模板变量差集一致。"""
    content = read_text(
        "project-info/demand/Stage13-Jenkins统一平台环境启动流水线/"
        "平台环境准备-Jenkins统一平台环境启动流水线-需求说明.md"
    )

    assert "新增项共 8 个" in content
    assert "新增项共 7 个" not in content


def test_readme_limits_manual_sync_worker_commands_to_isolated_local_debugging():
    """宿主机同步命令只能是隔离调试，不能被误作平台环境准备入口。"""
    content = read_text("README.md")

    for marker in [
        "仅用于隔离本地开发调试",
        "不属于平台环境准备",
        "jenkins-sync-worker",
        "Compose",
        "环境 Job",
        "AI 不得执行",
    ]:
        assert marker in content


def test_deployment_documents_actual_compose_service_and_default_jenkins_image_facts():
    """部署说明必须以当前 Compose 的服务和默认 Jenkins 工具镜像为事实来源。"""
    deployment = read_text("docker/DEPLOYMENT.md")
    compose = read_text("docker-compose.yml")

    for marker in [
        "默认 Compose 服务",
        "`mysql`",
        "`jenkins`",
        "`backend`",
        "`frontend`",
        "`jenkins-sync-worker`",
        "`api-runner`",
        "tools profile",
        "默认 Jenkins controller 构建 `docker/jenkins/Dockerfile` 工具链镜像",
        "aiapitest-jenkins:lts-jdk17-tools",
        "不是可选 override",
    ]:
        assert marker in deployment

    for service in ["mysql:", "jenkins:", "backend:", "frontend:", "jenkins-sync-worker:", "api-runner:"]:
        assert service in compose
    assert "dockerfile: docker/jenkins/Dockerfile" in compose
    assert "aiapitest-jenkins:lts-jdk17-tools" in compose


def test_all_agent_rules_lock_destructive_environment_prohibitions():
    """唯一入口规则必须同时拒绝破坏性 Docker 和数据库生命周期旁路。"""
    required_prohibitions = ["down -v", "volume 删除", "migration", "重新构建"]

    for path in AGENT_RULES:
        content = path.read_text(encoding="utf-8")
        missing = [marker for marker in required_prohibitions if marker not in content]
        assert not missing, f"{path.relative_to(ROOT)} missing Task5 destructive-operation rule: {missing}"


def test_deployment_never_calls_the_default_jenkins_tools_dockerfile_optional():
    """默认 Compose 已构建 tools 镜像，文档不能保留“可选”旧语义。"""
    deployment = read_text("docker/DEPLOYMENT.md")

    assert "`docker/jenkins/Dockerfile` | 可选 Jenkins 工具链镜像定义" not in deployment
    assert "`docker/jenkins/Dockerfile` | 默认 Jenkins tools 镜像构建来源" in deployment


def test_deployment_documents_required_private_application_database_user():
    """Compose 必填应用用户时，部署资料不能继续描述 root 默认或非 root 可选。"""
    compose = read_text("docker-compose.yml")
    deployment = read_text("docker/DEPLOYMENT.md")
    env_example = read_text(".env.example")

    assert "${DB_USER:?Set DB_USER in .env}" in compose
    assert "${DB_PASSWORD:?Set DB_PASSWORD in .env}" in compose
    for marker in [
        "`DB_USER`",
        "`DB_PASSWORD`",
        "必填",
        "应用专用非 root 数据库用户",
        "只写入本地 `.env`",
    ]:
        assert marker in deployment
        assert marker in env_example
    for obsolete in [
        "默认 root 连接优先",
        "默认 root 连接时",
        "只有启用非 root 用户时",
        "只有使用非 root 用户时",
        "如果后续启用非 root 用户",
        "`MYSQL_USER` / `MYSQL_PASSWORD`",
        "`MYSQL_PASSWORD`",
    ]:
        assert obsolete not in deployment

    password_troubleshooting = deployment.split("MySQL 密码不一致：", 1)[1].split(
        "## 环境 Job 创建与使用", 1
    )[0]
    for marker in [
        "`MYSQL_ROOT_PASSWORD`",
        "`DB_USER`",
        "`DB_PASSWORD`",
        "应用连接",
        "应用专用非 root 数据库用户",
        "持久化数据卷",
    ]:
        assert marker in password_troubleshooting


def test_heartbeat_template_describes_worker_container_health_only():
    """心跳阈值只影响 worker 容器健康，不直接改变 backend readiness。"""
    env_example = read_text(".env.example")

    assert "`jenkins-sync-worker` 容器 healthcheck 返回 unhealthy" in env_example
    assert "不直接改变 backend readiness" in env_example
    assert "超过该值 ready 检查返回未就绪" not in env_example
