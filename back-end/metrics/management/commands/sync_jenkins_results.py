from __future__ import annotations

import os
import signal
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError

from metrics.jenkins_sync import run_jenkins_sync_cycle


DEFAULT_POLL_INTERVAL_SECONDS = 10
HEARTBEAT_PATH_ENV = "JENKINS_SYNC_HEARTBEAT_PATH"


def heartbeat_path() -> Path:
    configured_path = os.getenv(HEARTBEAT_PATH_ENV, "").strip()
    if configured_path:
        return Path(configured_path)
    return Path(tempfile.gettempdir()) / "aiapitest-dwp" / "jenkins-sync-worker.heartbeat"


def write_heartbeat() -> None:
    target_path = heartbeat_path()
    temporary_path = target_path.with_name(f".{target_path.name}.{uuid4().hex}.tmp")
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        temporary_path.write_text(timestamp, encoding="utf-8")
        os.replace(temporary_path, target_path)
    except OSError as exc:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise CommandError("worker heartbeat write failed") from exc


class Command(BaseCommand):
    help = "单次或持续同步 Jenkins 运行中任务和每日全量构建。"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument("--once", action="store_true", help="执行一轮后退出（默认）。")
        mode.add_argument("--watch", action="store_true", help="按轮询间隔持续执行。")
        parser.add_argument("--interval", type=int, help="watch 模式轮询间隔秒数。")

    def handle(self, *args, **options):
        watch = bool(options.get("watch"))
        interval = options.get("interval")
        if interval is not None and not watch:
            raise CommandError("--interval can only be used with --watch")
        if interval is None:
            raw_interval = (
                os.getenv("JENKINS_BUILD_POLL_INTERVAL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS))
                or str(DEFAULT_POLL_INTERVAL_SECONDS)
            )
            try:
                interval = int(raw_interval)
            except ValueError:
                interval = DEFAULT_POLL_INTERVAL_SECONDS
            if interval <= 0:
                interval = DEFAULT_POLL_INTERVAL_SECONDS
            if str(interval) != raw_interval:
                self.stderr.write(
                    self.style.WARNING(
                        "JENKINS_BUILD_POLL_INTERVAL_SECONDS 无效，"
                        f"已回退为 {DEFAULT_POLL_INTERVAL_SECONDS} 秒。"
                    )
                )
        if interval <= 0:
            raise CommandError("interval must be a positive integer")

        stop_requested = False
        previous_sigterm_handler = None

        def request_stop(_signum, _frame):
            nonlocal stop_requested
            stop_requested = True

        if watch:
            # Compose 停止服务时会发送 SIGTERM，worker 应完成当前步骤后正常退出。
            previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, request_stop)

        try:
            while not stop_requested:
                stats = run_jenkins_sync_cycle()
                write_heartbeat()
                self.stdout.write(" ".join(f"{key}={value}" for key, value in stats.items()))
                if not watch:
                    return
                if stop_requested:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            stop_requested = True
        finally:
            if watch and previous_sigterm_handler is not None:
                signal.signal(signal.SIGTERM, previous_sigterm_handler)

        if stop_requested:
            self.stdout.write("Jenkins sync worker stopped.")
