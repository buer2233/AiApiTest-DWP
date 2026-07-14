from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    checks: dict[str, str]
    failed_check: str | None = None
    reason_code: str | None = None


def configuration_is_valid() -> bool:
    """检查进程启动所需的最小 Django 与数据库配置结构。"""
    try:
        secret_key = settings.SECRET_KEY
        allowed_hosts = settings.ALLOWED_HOSTS
        databases = settings.DATABASES
    except ImproperlyConfigured:
        return False

    if not isinstance(databases, Mapping):
        return False
    default_database = databases.get("default")
    if not isinstance(default_database, Mapping):
        return False

    required_database_values = (
        default_database.get("ENGINE"),
        default_database.get("NAME"),
    )
    return bool(
        secret_key
        and allowed_hosts
        and all(value is not None and str(value).strip() for value in required_database_values)
    )


def database_is_available() -> bool:
    """通过只读查询确认默认数据库连接可用。"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return False
    return True


def schema_is_ready() -> bool:
    """只读计算 migration plan，不执行任何 migration。"""
    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        return not executor.migration_plan(targets)
    except DatabaseError:
        raise
    except Exception:
        return False


def evaluate_readiness() -> ReadinessResult:
    checks = {
        "configuration": "unknown",
        "database": "unknown",
        "schema": "unknown",
    }

    if not configuration_is_valid():
        checks["configuration"] = "invalid"
        return ReadinessResult(
            ready=False,
            failed_check="configuration",
            reason_code="configuration_invalid",
            checks=checks,
        )
    checks["configuration"] = "valid"

    if not database_is_available():
        checks["database"] = "unavailable"
        return ReadinessResult(
            ready=False,
            failed_check="database",
            reason_code="database_unavailable",
            checks=checks,
        )
    checks["database"] = "available"

    try:
        schema_ready = schema_is_ready()
    except DatabaseError:
        checks["database"] = "unavailable"
        return ReadinessResult(
            ready=False,
            failed_check="database",
            reason_code="database_unavailable",
            checks=checks,
        )

    if not schema_ready:
        checks["schema"] = "not_ready"
        return ReadinessResult(
            ready=False,
            failed_check="schema",
            reason_code="schema_not_ready",
            checks=checks,
        )
    checks["schema"] = "ready"
    return ReadinessResult(ready=True, checks=checks)
