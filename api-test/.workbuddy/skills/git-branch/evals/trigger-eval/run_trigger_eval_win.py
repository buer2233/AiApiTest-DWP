#!/usr/bin/env python3
"""支持检查点续跑的 Windows 兼容 git-branch 触发评估器。

默认探针为本目录下的 skill_probe.py（确定性规则模式），每条查询都有明确
判定，accuracy 数值可复现；也可用 ``--command "claude -p"`` 等切换为无头
模型实测探针。仅当探针明确给出触发判定时才计入结果；超时、命令缺失和空
输出保留为 ``INCONCLUSIVE``（吸取一期 T1.6 教训：默认探针保证不空跑）。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable


SKILL_NAME = "git-branch"
Probe = Callable[[str, int], tuple[bool | None, str, float]]


def normalize_eval_set(payload: Any) -> list[dict[str, Any]]:
    """接受当前结构化评估集和兼容的旧版列表格式。"""
    cases = payload.get("cases") if isinstance(payload, dict) else payload
    if not isinstance(cases, list):
        raise ValueError("评估集必须是列表或包含 cases 的对象")
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"第 {index} 条评估用例必须是对象")
        if not isinstance(case.get("query"), str) or not isinstance(
            case.get("should_trigger"), bool
        ):
            raise ValueError(f"第 {index} 条评估用例需要 query 和 should_trigger")
    return cases


def _job_key(query_index: int, run_index: int) -> str:
    return f"q{query_index}-r{run_index}"


def load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    jobs = payload.get("jobs", {})
    return jobs if isinstance(jobs, dict) else {}


def save_checkpoint(path: Path, jobs: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "completed": len(jobs),
        "jobs": jobs,
    }
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _parse_probe_output(stdout: str, skill_name: str) -> tuple[bool | None, str]:
    text = stdout.strip()
    if not text:
        return None, "no_signal"
    lowered = text.lower()
    if "skill_triggered" in lowered or f"skills/{skill_name.lower()}" in lowered:
        return True, "skill_hit"
    if "skill_not_triggered" in lowered:
        return False, "explicit_miss"
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and isinstance(event.get("triggered"), bool):
            return event["triggered"], "structured_result"
        if event.get("type") == "result":
            return False, "result_without_skill"
    return None, "no_signal"


def _split_command(command: str) -> list[str]:
    """按 Windows 习惯切分命令：双引号成组，其余按空白切分。

    shlex.split 的 posix=False 模式会保留引号、posix=True 模式会吞掉
    Windows 路径里的反斜杠，两者都会让带引号的 python 路径无法执行，
    因此这里用显式的正则切分。
    """
    parts: list[str] = []
    for quoted, bare in re.findall(r'"([^"]*)"|(\S+)', command):
        parts.append(quoted if quoted else bare)
    return parts


def build_subprocess_probe(command: str, skill_name: str, project_root: Path) -> Probe:
    command_parts = _split_command(command)
    if not command_parts:
        raise ValueError("探针命令不能为空")

    def probe(query: str, timeout: int) -> tuple[bool | None, str, float]:
        started = time.monotonic()
        try:
            completed = subprocess.run(
                [*command_parts, query],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return None, "timeout", round(time.monotonic() - started, 3)
        except OSError:
            return None, "command_unavailable", round(time.monotonic() - started, 3)
        decision, detail = _parse_probe_output(completed.stdout, skill_name)
        if decision is None and completed.returncode != 0:
            detail = f"no_signal_exit_{completed.returncode}"
        return decision, detail, round(time.monotonic() - started, 3)

    return probe


def run_jobs(
    *,
    cases: list[dict[str, Any]],
    jobs: dict[str, dict[str, Any]],
    runs_per_query: int,
    timeout: int,
    num_workers: int,
    checkpoint_path: Path,
    evaluator: Probe,
) -> dict[str, dict[str, Any]]:
    """仅运行缺失任务，并在每个结果生成后原子写入检查点。"""
    pending = [
        (query_index, run_index, case)
        for query_index, case in enumerate(cases)
        for run_index in range(runs_per_query)
        if _job_key(query_index, run_index) not in jobs
    ]
    lock = threading.Lock()

    def evaluate(
        query_index: int, run_index: int, case: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        try:
            triggered, detail, elapsed = evaluator(case["query"], timeout)
        except Exception as exc:  # noqa: BLE001 - 保留可续跑的结果
            triggered, detail, elapsed = None, f"probe_error:{type(exc).__name__}", 0.0
        return _job_key(query_index, run_index), {
            "query_index": query_index,
            "run_index": run_index,
            "case_id": case.get("id"),
            "should_trigger": case["should_trigger"],
            "triggered": triggered,
            "detail": detail,
            "elapsed_sec": elapsed,
        }

    with ThreadPoolExecutor(max_workers=max(1, num_workers)) as executor:
        futures = {
            executor.submit(evaluate, query_index, run_index, case): None
            for query_index, run_index, case in pending
        }
        for future in as_completed(futures):
            key, result = future.result()
            with lock:
                jobs[key] = result
                save_checkpoint(checkpoint_path, jobs)
    return jobs


def aggregate(
    cases: list[dict[str, Any]],
    jobs: dict[str, dict[str, Any]],
    *,
    runs_per_query: int,
    threshold: float,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for query_index, case in enumerate(cases):
        decisive: list[bool] = []
        details: list[str] = []
        inconclusive_runs = 0
        for run_index in range(runs_per_query):
            job = jobs.get(_job_key(query_index, run_index))
            if not job or job.get("triggered") is None:
                inconclusive_runs += 1
                details.append((job or {}).get("detail", "pending"))
                continue
            decisive.append(bool(job["triggered"]))
            details.append(str(job.get("detail", "")))
        should_trigger = case["should_trigger"]
        trigger_rate = sum(decisive) / len(decisive) if decisive else None
        if trigger_rate is None:
            status = "INCONCLUSIVE"
            passed: bool | None = None
        else:
            passed = trigger_rate >= threshold if should_trigger else trigger_rate < threshold
            status = "PASS" if passed else "FAIL"
        results.append(
            {
                "id": case.get("id"),
                "query": case["query"],
                "should_trigger": should_trigger,
                "trigger_rate": trigger_rate,
                "decisive_runs": len(decisive),
                "inconclusive_runs": inconclusive_runs,
                "details": details,
                "status": status,
                "pass": passed,
            }
        )
    assessed = [result for result in results if result["pass"] is not None]
    passed_count = sum(result["pass"] is True for result in assessed)
    return {
        "results": results,
        "summary": {
            "total": len(results),
            "assessed": len(assessed),
            "passed": passed_count,
            "failed": len(assessed) - passed_count,
            "inconclusive": len(results) - len(assessed),
            "inconclusive_runs": sum(result["inconclusive_runs"] for result in results),
            "accuracy": passed_count / len(assessed) if assessed else None,
        },
    }


def write_results(path: Path, report: dict[str, Any], config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"config": config, **report}
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _default_paths() -> tuple[Path, Path, Path]:
    """返回（默认探针命令路径、默认输出目录、api-test-E9 仓库根）。"""
    evals_root = Path(__file__).resolve().parents[1]
    # git-branch 目录向上三级：skills -> .workbuddy -> api-test-E9
    api_root = evals_root.parent.parents[2]
    probe_path = Path(__file__).resolve() / ".." / "skill_probe.py"
    return probe_path.resolve(), api_root / "runtime" / "trigger-eval" / "git-branch", api_root


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    probe_path, default_output_dir, api_root = _default_paths()
    evals_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="在 Windows 上运行 git-branch 触发评估。")
    parser.add_argument("--eval-set", type=Path, default=evals_root / "trigger_eval_set.json")
    parser.add_argument("--skill-path", type=Path, default=evals_root.parent)
    parser.add_argument("--project-root", type=Path, default=api_root)
    parser.add_argument(
        "--command",
        default=f'"{sys.executable}" "{probe_path}"',
        help="探针命令前缀；会自动追加查询文本。默认使用确定性技能探针。",
    )
    parser.add_argument("--output", type=Path, default=default_output_dir / "full_results.json")
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--num-workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--runs-per-query", type=int, default=3)
    parser.add_argument("--trigger-threshold", type=float, default=0.5)
    args = parser.parse_args()
    if args.timeout <= 0 or args.num_workers <= 0 or args.runs_per_query <= 0:
        parser.error("timeout、num-workers 和 runs-per-query 必须为正数")
    if not 0 < args.trigger_threshold <= 1:
        parser.error("trigger-threshold 必须位于 (0, 1] 区间")

    payload = json.loads(args.eval_set.read_text(encoding="utf-8"))
    cases = normalize_eval_set(payload)
    checkpoint = args.checkpoint or args.output.with_name("checkpoint.json")
    jobs = load_checkpoint(checkpoint)
    probe = build_subprocess_probe(args.command, SKILL_NAME, args.project_root.resolve())
    run_jobs(
        cases=cases,
        jobs=jobs,
        runs_per_query=args.runs_per_query,
        timeout=args.timeout,
        num_workers=args.num_workers,
        checkpoint_path=checkpoint,
        evaluator=probe,
    )
    report = aggregate(
        cases, jobs, runs_per_query=args.runs_per_query, threshold=args.trigger_threshold
    )
    config = {
        "eval_set": str(args.eval_set),
        "skill_path": str(args.skill_path),
        "project_root": str(args.project_root.resolve()),
        "command": args.command,
        "runs_per_query": args.runs_per_query,
        "timeout": args.timeout,
        "num_workers": args.num_workers,
        "trigger_threshold": args.trigger_threshold,
    }
    write_results(args.output, report, config)
    print(json.dumps({"output": str(args.output), "checkpoint": str(checkpoint), **report["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
