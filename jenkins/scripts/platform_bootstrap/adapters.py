"""外部命令适配器；业务逻辑通过依赖注入使用该边界。"""

from __future__ import annotations

import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

from .models import CommandResult, CommandSpec, HttpRequest, HttpResponse
from .security import Redactor


class SubprocessCommandRunner:
    """使用 argv 和 shell=False 执行一次命令，不做任何自动重试。"""

    def __init__(
        self,
        *,
        redactor: Redactor | None = None,
        popen_factory: Callable[..., object] = subprocess.Popen,
        output_tail_limit: int = 40_000,
    ):
        self._redactor = redactor or Redactor()
        self._popen_factory = popen_factory
        self._output_tail_limit = output_tail_limit

    def _failure_result(
        self,
        spec: CommandSpec,
        *,
        started: float,
        returncode: int,
        message: str,
        timed_out: bool = False,
    ) -> CommandResult:
        """将基础设施异常降级为脱敏命令失败，供上层生成结构化诊断。"""
        redacted = self._redactor.text(message)
        self._write_evidence(spec.evidence_path, redacted)
        print(redacted)
        return CommandResult(
            returncode=returncode,
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
            redacted_output_tail=redacted[-self._output_tail_limit :],
            evidence_path=str(spec.evidence_path),
        )

    def _write_evidence(self, path: Path, content: str) -> bool:
        try:
            path.write_text(content, encoding="utf-8")
        except OSError:
            return False
        return True

    @staticmethod
    def _remaining_seconds(deadline: float) -> float:
        return max(0.0, deadline - time.monotonic())

    def run(self, spec: CommandSpec) -> CommandResult:
        started = time.monotonic()
        deadline = started + max(0.0, float(spec.timeout_seconds))
        try:
            spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            return self._failure_result(
                spec,
                started=started,
                returncode=125,
                message=(
                    "COMMAND_EVIDENCE_DIRECTORY_UNAVAILABLE: unable to prepare "
                    "command evidence directory; inspect Jenkins workspace permissions."
                ),
            )
        environment = os.environ.copy()
        if spec.env:
            environment.update(spec.env)
        try:
            process = self._popen_factory(
                list(spec.argv),
                cwd=str(spec.cwd),
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
            )
        except OSError:
            message = (
                "COMMAND_START_FAILED: unable to start external command; inspect "
                "the executable, workspace, and Jenkins agent permissions."
            )
            if not self._write_evidence(spec.evidence_path, self._redactor.text(message)):
                message += (
                    " COMMAND_EVIDENCE_WRITE_FAILED: command evidence could not be "
                    "persisted; inspect Jenkins workspace permissions."
                )
            return self._failure_result(
                spec,
                started=started,
                returncode=127,
                message=message,
            )
        timed_out = False
        output = ""
        try:
            if hasattr(process, "communicate"):
                output, _ = process.communicate(
                    timeout=self._remaining_seconds(deadline)
                )
            else:
                process.wait(timeout=self._remaining_seconds(deadline))
                output = "".join(process.stdout or ())
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup_failed = False
            try:
                process.terminate()
            except OSError:
                cleanup_failed = True
            if not cleanup_failed and self._remaining_seconds(deadline) > 0:
                try:
                    if hasattr(process, "communicate"):
                        remaining, _ = process.communicate(
                            timeout=self._remaining_seconds(deadline)
                        )
                        output += remaining or ""
                    else:
                        process.wait(timeout=self._remaining_seconds(deadline))
                except subprocess.TimeoutExpired:
                    try:
                        process.kill()
                    except OSError:
                        cleanup_failed = True
                    if not cleanup_failed and self._remaining_seconds(deadline) > 0:
                        try:
                            if hasattr(process, "communicate"):
                                remaining, _ = process.communicate(
                                    timeout=self._remaining_seconds(deadline)
                                )
                                output += remaining or ""
                            else:
                                process.wait(timeout=self._remaining_seconds(deadline))
                        except (OSError, subprocess.TimeoutExpired):
                            cleanup_failed = True
                except OSError:
                    cleanup_failed = True
            if cleanup_failed:
                return self._failure_result(
                    spec,
                    started=started,
                    returncode=124,
                    timed_out=True,
                    message=(
                        "COMMAND_TIMEOUT_CLEANUP_FAILED: timed-out command cleanup "
                        "could not complete; inspect Jenkins agent process permissions."
                    ),
                )
        except OSError:
            return self._failure_result(
                spec,
                started=started,
                returncode=125,
                message=(
                    "COMMAND_EXECUTION_FAILED: command I/O failed without exposing "
                    "system error details; inspect Jenkins agent permissions."
                ),
            )
        redacted = self._redactor.text(output)
        if not self._write_evidence(spec.evidence_path, redacted):
            return self._failure_result(
                spec,
                started=started,
                returncode=125,
                message=(
                    "COMMAND_EVIDENCE_WRITE_FAILED: command output could not be "
                    "persisted; inspect Jenkins workspace permissions. " + redacted
                ),
            )
        if redacted:
            print(redacted, end="" if redacted.endswith("\n") else "\n")
        returncode = getattr(process, "returncode", -1)
        if timed_out and returncode is None:
            returncode = 124
        return CommandResult(
            returncode=int(returncode if returncode is not None else -1),
            duration_seconds=time.monotonic() - started,
            timed_out=timed_out,
            redacted_output_tail=redacted[-self._output_tail_limit :],
            evidence_path=str(spec.evidence_path),
        )


class UrllibHttpClient:
    """不记录 Authorization、Cookie 或请求体的标准库 HTTP 适配器。"""

    def __init__(self, *, max_response_bytes: int = 1_000_000):
        self.max_response_bytes = max_response_bytes

    def request(self, request: HttpRequest) -> HttpResponse:
        native_request = urllib.request.Request(
            request.url,
            data=request.body,
            headers=dict(request.headers),
            method=request.method,
        )
        try:
            with urllib.request.urlopen(native_request, timeout=request.timeout_seconds) as response:
                body = response.read(self.max_response_bytes + 1)[: self.max_response_bytes]
                return HttpResponse(
                    status=int(response.status),
                    headers=dict(response.headers.items()),
                    body=body,
                )
        except urllib.error.HTTPError as exc:
            body = exc.read(self.max_response_bytes + 1)[: self.max_response_bytes]
            return HttpResponse(status=int(exc.code), headers=dict(exc.headers.items()), body=body)
