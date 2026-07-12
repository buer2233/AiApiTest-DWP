from __future__ import annotations

import logging

from metrics.jenkins_service import JenkinsServiceError, discover_jenkins_builds, fetch_jenkins_task_result
from metrics.models import JenkinsJobBinding, JenkinsTask, TestRun
from metrics.views import (
    ACTIVE_TASK_STATUSES,
    TERMINAL_TASK_STATUSES,
    create_or_get_daily_task_from_discovery,
    expire_stale_jenkins_task,
    jenkins_task_is_stale,
    sync_task_with_result,
)


logger = logging.getLogger(__name__)


def _empty_stats() -> dict[str, int]:
    return {
        "active_processed": 0,
        "daily_discovered": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
    }


def run_jenkins_sync_cycle() -> dict[str, int]:
    """执行一轮 Jenkins 同步；单任务失败隔离，下一轮可自动恢复。"""
    stats = _empty_stats()
    active_tasks = list(
        JenkinsTask.objects.select_related("run")
        .filter(status__in=ACTIVE_TASK_STATUSES)
        .order_by("created_at", "id")
    )
    for task in active_tasks:
        stats["active_processed"] += 1
        try:
            result = fetch_jenkins_task_result(task)
            if result.get("queue_pending") and jenkins_task_is_stale(task):
                expire_stale_jenkins_task(task, f"status={task.status}, task_id={task.id}")
            else:
                sync_task_with_result(task, result)
            stats["synced"] += 1
        except JenkinsServiceError as exc:
            stats["failed"] += 1
            logger.warning(
                "Jenkins active task sync failed: task_id=%s error_type=%s",
                task.id,
                type(exc).__name__,
            )

    bindings = list(
        JenkinsJobBinding.objects.select_related("environment", "module")
        .filter(task_type=TestRun.RunType.DAILY_FULL, is_active=True)
        .order_by("job_full_name", "id")
    )
    for binding in bindings:
        try:
            discovered = discover_jenkins_builds(job_full_names=[binding.job_full_name])
        except JenkinsServiceError as exc:
            stats["failed"] += 1
            logger.warning(
                "Jenkins Daily Job discovery failed: binding_id=%s error_type=%s",
                binding.id,
                type(exc).__name__,
            )
            continue
        for build_result in discovered:
            stats["daily_discovered"] += 1
            task, _ = create_or_get_daily_task_from_discovery(binding, build_result)
            task.refresh_from_db()
            if task.status in TERMINAL_TASK_STATUSES:
                stats["skipped"] += 1
                continue
            try:
                result = fetch_jenkins_task_result(task)
                sync_task_with_result(task, result)
                stats["synced"] += 1
            except JenkinsServiceError as exc:
                stats["failed"] += 1
                logger.warning(
                    "Jenkins Daily build sync failed: task_id=%s error_type=%s",
                    task.id,
                    type(exc).__name__,
                )
    return stats
