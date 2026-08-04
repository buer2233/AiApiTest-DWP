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
  echo "Created .env from .env.example. Add the private configuration documented in docker/DEPLOYMENT.md, then rerun this script." >&2
  exit 2
fi

set_private_env_value() {
  local key="$1"
  local value="$2"
  local tmp_file

  if grep -Eq "^[[:space:]]*${key}=" .env; then
    tmp_file="$(mktemp)"
    awk -v key="${key}" -v value="${value}" '
      BEGIN { replacement = key "=" value }
      $0 ~ "^[[:space:]]*" key "=" { $0 = replacement }
      { print }
    ' .env >"${tmp_file}"
    mv "${tmp_file}" .env
  else
    printf '\n%s=%s\n' "${key}" "${value}" >>.env
  fi
}

dotenv_value() {
  local value="$1"
  value="$(printf '%s' "${value}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
  case "${value}" in
    \"*) value="${value#\"}"; value="${value%%\"*}" ;;
    \'*) value="${value#\'}"; value="${value%%\'*}" ;;
    *) value="$(printf '%s' "${value}" | sed -E 's/[[:space:]]+#.*$//; s/[[:space:]]+$//')" ;;
  esac
  printf '%s' "${value}"
}

read_env_value() {
  local key="$1"
  local raw
  raw="$(grep -E "^${key}=" .env | head -n 1 | cut -d= -f2- || true)"
  dotenv_value "${raw}"
}

format_host_port_host() {
  local host="$1"
  host="${host#[}"
  host="${host%]}"
  if [[ "${host}" == *:* ]]; then
    printf '[%s]' "${host}"
  else
    printf '%s' "${host}"
  fi
}

# 只启动平台依赖的 MySQL 和 Jenkins，保留已有数据卷。
docker compose up -d mysql jenkins
docker compose ps

# 本地 Jenkins init 脚本会生成运行时 API token；写入私有 .env，后端重启后才能携带 crumb 触发 Job。
JENKINS_API_CREDENTIAL=""
for _ in $(seq 1 30); do
  JENKINS_API_CREDENTIAL="$(docker exec aiapitest-jenkins sh -lc 'cat /var/jenkins_home/aiapitest-local-api-token.txt 2>/dev/null || true' | tr -d '\r' || true)"
  if printf '%s' "${JENKINS_API_CREDENTIAL}" | grep -Eq '^[^:]+:.+'; then
    break
  fi
  sleep 1
done
if printf '%s' "${JENKINS_API_CREDENTIAL}" | grep -Eq '^[^:]+:.+'; then
  JENKINS_API_USERNAME="${JENKINS_API_CREDENTIAL%%:*}"
  JENKINS_API_TOKEN="${JENKINS_API_CREDENTIAL#*:}"
  set_private_env_value "JENKINS_USERNAME" "${JENKINS_API_USERNAME}"
  set_private_env_value "JENKINS_API_TOKEN" "${JENKINS_API_TOKEN}"
  echo "Injected local Jenkins API credentials into private .env. Restart the backend to reload them."
else
  echo "Local Jenkins API token was not ready. Re-run this script after Jenkins finishes startup." >&2
fi

# 地址提示与应用相同，都从平台公开主机、协议和服务端口派生。
PLATFORM_PUBLIC_HOST="$(read_env_value 'PLATFORM_PUBLIC_HOST')"
PLATFORM_PUBLIC_SCHEME="$(read_env_value 'PLATFORM_PUBLIC_SCHEME')"
JENKINS_HTTP_PORT="$(read_env_value 'JENKINS_HTTP_PORT')"
MYSQL_HOST_PORT="$(read_env_value 'MYSQL_HOST_PORT')"
PUBLIC_DISPLAY_HOST="$(format_host_port_host "${PLATFORM_PUBLIC_HOST:-127.0.0.1}")"

echo
echo "Jenkins: ${PLATFORM_PUBLIC_SCHEME:-http}://${PUBLIC_DISPLAY_HOST}:${JENKINS_HTTP_PORT:-8080}"
echo "MySQL: ${PUBLIC_DISPLAY_HOST}:${MYSQL_HOST_PORT:-3307}"
echo "Initial Jenkins password:"
echo "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
