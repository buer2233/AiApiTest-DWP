#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

command -v docker >/dev/null 2>&1 || {
  echo "Docker is not installed or is not available in PATH." >&2
  exit 1
}

docker compose version >/dev/null

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example. Review MYSQL_ROOT_PASSWORD before shared use."
fi

docker compose up -d mysql jenkins
docker compose ps

JENKINS_HTTP_PORT="$(grep -E '^JENKINS_HTTP_PORT=' .env | cut -d= -f2- || true)"
MYSQL_HOST_PORT="$(grep -E '^MYSQL_HOST_PORT=' .env | cut -d= -f2- || true)"

echo
echo "Jenkins: http://localhost:${JENKINS_HTTP_PORT:-8080}"
echo "MySQL: 127.0.0.1:${MYSQL_HOST_PORT:-3307}"
echo "Initial Jenkins password:"
echo "  docker exec aiapitest-jenkins cat /var/jenkins_home/secrets/initialAdminPassword"
