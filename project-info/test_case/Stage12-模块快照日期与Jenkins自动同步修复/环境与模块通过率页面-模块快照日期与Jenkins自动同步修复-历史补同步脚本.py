from types import SimpleNamespace

from django.db import transaction

from metrics.jenkins_service import fetch_jenkins_task_result
from metrics.models import JenkinsTask, ModuleSnapshot, TestRun
from metrics.views import TERMINAL_TASK_STATUSES, sync_task_with_result


LEGACY_JOB_NAME = "AiApiTest-DWP-Daily-Full-Module"
BUILD_NUMBERS = (20, 21)
TARGET_SNAPSHOT_ID = 2
EXPECTED_PACKAGE_NAME = "test_gbif_case_module2"


snapshot = ModuleSnapshot.objects.select_related("environment", "module").get(id=TARGET_SNAPSHOT_ID)
if snapshot.module.package_name != EXPECTED_PACKAGE_NAME:
    raise RuntimeError("目标快照模块与预期 package_name 不一致，停止补同步。")

for build_number in BUILD_NUMBERS:
    existing_task = JenkinsTask.objects.select_related("run").filter(
        job_full_name=LEGACY_JOB_NAME,
        build_number=build_number,
    ).first()
    if existing_task and existing_task.status in TERMINAL_TASK_STATUSES:
        print(f"SKIP build={build_number} task={existing_task.id} status={existing_task.status}")
        continue

    run_key = (
        existing_task.run.run_key
        if existing_task and existing_task.run
        else f"jenkins-{LEGACY_JOB_NAME}-{build_number}"
    )
    probe = SimpleNamespace(
        job_full_name=LEGACY_JOB_NAME,
        build_number=build_number,
        queue_id="",
        run=SimpleNamespace(run_key=run_key),
    )
    result = fetch_jenkins_task_result(probe)
    summary = result.get("summary") or {}
    node_ids = [item.get("node_id", "") for item in summary.get("case_results") or []]
    expected_prefix = f"test_case/{EXPECTED_PACKAGE_NAME}/"
    if not node_ids or any(not node_id.startswith(expected_prefix) for node_id in node_ids):
        raise RuntimeError(f"build {build_number} artifact 模块归属校验失败，停止补同步。")

    with transaction.atomic():
        run, _ = TestRun.objects.get_or_create(
            run_key=run_key,
            defaults={
                "run_type": TestRun.RunType.DAILY_FULL,
                "environment": snapshot.environment,
                "module": snapshot.module,
                "status": TestRun.Status.RUNNING,
            },
        )
        task, _ = JenkinsTask.objects.get_or_create(
            job_full_name=LEGACY_JOB_NAME,
            build_number=build_number,
            defaults={
                "run": run,
                "environment": snapshot.environment,
                "module": snapshot.module,
                "task_type": TestRun.RunType.DAILY_FULL,
                "trigger_source": JenkinsTask.TriggerSource.JENKINS_CRON,
                "status": TestRun.Status.RUNNING,
            },
        )

    synced = sync_task_with_result(task, result)
    print(
        f"SYNC build={build_number} task={synced.id} status={synced.status} "
        f"finished_at={synced.finished_at.isoformat() if synced.finished_at else ''}"
    )
