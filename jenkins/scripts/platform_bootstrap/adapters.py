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

    def run(self, spec: CommandSpec) -> CommandResult:
        spec.evidence_path.parent.mkdir(parents=True, exist_ok=True)
        environment = os.environ.copy()
        if spec.env:
            environment.update(spec.env)
        started = time.monotonic()
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
        timed_out = False
        output = ""
        try:
            if hasattr(process, "communicate"):
                output, _ = process.communicate(timeout=spec.timeout_seconds)
            else:
                output = "".join(process.stdout or ())
                process.wait(timeout=spec.timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                if hasattr(process, "communicate"):
                    remaining, _ = process.communicate(timeout=5)
                    output += remaining or ""
                else:
                    process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                if hasattr(process, "communicate"):
                    remaining, _ = process.communicate()
                    output += remaining or ""
        redacted = self._redactor.text(output)
        spec.evidence_path.write_text(redacted, encoding="utf-8")
        if redacted:
            print(redacted, end="" if redacted.endswith("\n") else "\n")
        returncode = getattr(process, "returncode", -1)
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
