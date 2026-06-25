#!/usr/bin/env bash
# Docker 快速部署脚本（Linux/macOS/Git Bash）。
# 本脚本在仓库根目录启动 MySQL 和 Jenkins 两个基础服务，
# 不负责启动后端、前端或 api-test 应用进程。
set -euo pipefail

# 解析脚本所在目录，再切换到仓库根目录执行 docker compose。
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Docker CLI 是后续 compose 操作的硬依赖，缺失时直接中止并给出明确错误。
command -v docker >/dev/null 2>&1 || {
  echo "Docker is not installed or is not available in PATH." >&2
  exit 1
}

# 提前确认 Docker Compose v2 可用，避免执行到服务启动阶段才失败。
docker compose version >/dev/null

# .env 是本地私有配置，不提交 git；首次部署时从模板复制一份。
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review MYSQL_ROOT_PASSWORD before shared use."
fi

# 只启动平台依赖的 MySQL 和 Jenkins，保留已有数据卷。
docker compose up -d mysql jenkins
docker compose ps

# 从 .env 读取端口并输出访问提示；读取不到时回退到 Compose 默认端口。
JENKINS_HTTP_PORT="$(grep -E '^JENKINS_HTTP_PORT=' .env | cut -d= -f2- || true)"
MYSQL_HOST_PORT="$(grep -E '^MYSQL_HOST_PORT=' .env | cut -d= -f2- || true)"

echo
echo "Jenkins: http://localhost:${JENKINS_HTTP_PORT:-8080}"
echo "MySQL: 127.0.0.1:${MYSQL_HOST_PORT:-3307}"
echo "Initial Jenkins password:"
echo "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
