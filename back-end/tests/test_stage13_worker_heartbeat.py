from __future__ import annotations

import os
from datetime import datetime
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError


pytestmark = pytest.mark.command


SYNC_STATS = {
    "active_processed": 0,
    "daily_discovered": 0,
    "synced": 0,
    "failed": 0,
    "skipped": 0,
}


def assert_timestamp_only(path) -> None:
    content = path.read_text(encoding="utf-8")
    assert content == content.strip()
    assert "\n" not in content
    parsed = datetime.fromisoformat(content.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_sync_worker_writes_custom_heartbeat_atomically_after_successful_cycle(tmp_path, monkeypatch):
    heartbeat_path = tmp_path / "worker" / "heartbeat"
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        return_value=SYNC_STATS,
    ), patch(
        "metrics.management.commands.sync_jenkins_results.os.replace",
        wraps=os.replace,
    ) as replace:
        call_command("sync_jenkins_results", once=True, stdout=StringIO())

    assert_timestamp_only(heartbeat_path)
    replace.assert_called_once()
    source, destination = replace.call_args.args
    assert destination == heartbeat_path
    assert source.parent == heartbeat_path.parent
    assert not source.exists()


def test_sync_worker_default_heartbeat_path_uses_system_temp_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("JENKINS_SYNC_HEARTBEAT_PATH", raising=False)

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        return_value=SYNC_STATS,
    ), patch("tempfile.gettempdir", return_value=str(tmp_path)):
        call_command("sync_jenkins_results", once=True, stdout=StringIO())

    heartbeat_path = tmp_path / "aiapitest-dwp" / "jenkins-sync-worker.heartbeat"
    assert_timestamp_only(heartbeat_path)


def test_sync_worker_watch_updates_heartbeat_after_every_successful_cycle(tmp_path, monkeypatch):
    heartbeat_path = tmp_path / "heartbeat"
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        side_effect=[SYNC_STATS, SYNC_STATS, KeyboardInterrupt],
    ), patch(
        "metrics.management.commands.sync_jenkins_results.time.sleep",
    ), patch(
        "metrics.management.commands.sync_jenkins_results.os.replace",
        wraps=os.replace,
    ) as replace:
        call_command("sync_jenkins_results", watch=True, interval=1, stdout=StringIO())

    assert replace.call_count == 2
    assert_timestamp_only(heartbeat_path)


def test_sync_worker_heartbeat_write_failure_is_explicit_and_nonzero(tmp_path, monkeypatch):
    heartbeat_path = tmp_path / "heartbeat"
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        return_value=SYNC_STATS,
    ), patch(
        "metrics.management.commands.sync_jenkins_results.os.replace",
        side_effect=OSError("controlled disk failure"),
    ), pytest.raises(CommandError, match="heartbeat"):
        call_command("sync_jenkins_results", once=True, stdout=StringIO())

    assert not heartbeat_path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_sync_worker_does_not_write_heartbeat_when_sync_cycle_fails(tmp_path, monkeypatch):
    heartbeat_path = tmp_path / "heartbeat"
    monkeypatch.setenv("JENKINS_SYNC_HEARTBEAT_PATH", str(heartbeat_path))

    with patch(
        "metrics.management.commands.sync_jenkins_results.run_jenkins_sync_cycle",
        side_effect=RuntimeError("controlled sync failure"),
    ), pytest.raises(RuntimeError, match="controlled sync failure"):
        call_command("sync_jenkins_results", once=True, stdout=StringIO())

    assert not heartbeat_path.exists()
