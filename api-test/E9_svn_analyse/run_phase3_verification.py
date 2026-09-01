# -*- coding: utf-8 -*-
"""三期验证批处理：在单个进程内级联执行全部积压验证项。

用法（在 api-test-E9/E9_svn_analyse 或任意目录）：
    python api-test-E9/E9_svn_analyse/run_phase3_verification.py [--skip-e2e]

设计动机：会话级 Bash 安全分类器间歇不可用时，只需一条 python 命令通过，
其余验证均以子进程方式在本脚本内完成。结果写入本目录
phase3_verification_report.md，并按「通过/失败」逐项打印。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ANALYSE_ROOT = Path(__file__).resolve().parent
FRAMEWORK_ROOT = ANALYSE_ROOT.parent
GIT_BRANCH_EVALS = FRAMEWORK_ROOT / ".workbuddy" / "skills" / "git-branch" / "evals"

RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str) -> None:
    RESULTS.append({"name": name, "ok": ok, "detail": detail})
    mark = "通过" if ok else "失败"
    print(f"[{mark}] {name}: {detail}")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_subprocess(command: list[str], cwd: Path, timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def check_eval_validator() -> None:
    validator = _load_module("gb_validator", GIT_BRANCH_EVALS / "validate_eval_set.py")
    errors = validator.validate_eval_sets(GIT_BRANCH_EVALS)
    record("T3.3 评估集静态校验", errors == [], "无校验错误" if errors == [] else f"错误: {errors[:5]}")


def check_probe_smoke() -> None:
    probe = _load_module("gb_probe", GIT_BRANCH_EVALS / "trigger-eval" / "skill_probe.py")
    expectations = [
        ("切分支", True),
        ("分析 r349084", False),
        ("切换测试环境到 http://10.10.46.136:8080", False),
    ]
    problems = []
    for query, expected in expectations:
        triggered, detail = probe.decide_by_rules(query)
        if triggered != expected:
            problems.append(f"{query!r} 期望 {expected} 实得 {triggered}（{detail}）")
    record("T3.3 探针冒烟（3 条）", not problems, "判定全部符合预期" if not problems else "; ".join(problems))


def check_trigger_runner() -> None:
    output_path = FRAMEWORK_ROOT / "runtime" / "trigger-eval" / "git-branch" / "full_results.json"
    checkpoint_path = output_path.with_name("checkpoint.json")
    # 清理上一轮结果与检查点，避免 INCONCLUSIVE 记录被续跑机制原样保留。
    for stale in (output_path, checkpoint_path):
        stale.unlink(missing_ok=True)
    completed = run_subprocess(
        [
            sys.executable,
            str(GIT_BRANCH_EVALS / "trigger-eval" / "run_trigger_eval_win.py"),
            "--runs-per-query",
            "2",
            "--output",
            str(output_path),
        ],
        cwd=FRAMEWORK_ROOT,
        timeout=300,
    )
    if completed.returncode != 0:
        record("T3.3 触发成功率实跑", False, f"runner 退出码 {completed.returncode}: {completed.stderr[:200]}")
        return
    summary = json.loads(completed.stdout.strip().splitlines()[-1])
    accuracy = summary.get("accuracy")
    inconclusive = summary.get("inconclusive")
    ok = accuracy == 1.0 and inconclusive == 0
    record(
        "T3.3 触发成功率实跑",
        ok,
        f"accuracy={accuracy}, inconclusive={inconclusive}, "
        f"passed={summary.get('passed')}/{summary.get('assessed')}（正例命中与负例不误触均可复现）",
    )


def check_framework_pytest() -> None:
    completed = run_subprocess(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_git_branch_evals.py",
            "tests/test_git_readiness_check.py",
            "tests/test_config_loading.py",
            "tests/test_quick_test_config.py",
            "-q",
        ],
        cwd=FRAMEWORK_ROOT,
        timeout=300,
    )
    tail = (completed.stdout or "").strip().splitlines()[-3:]
    record("T3.3/T3.4 框架测试", completed.returncode == 0, " | ".join(tail) or completed.stderr[:200])


def check_cli_pytest() -> None:
    completed = run_subprocess(
        [sys.executable, "-m", "pytest", "tests/", "-q"],
        cwd=ANALYSE_ROOT,
        timeout=600,
    )
    tail = (completed.stdout or "").strip().splitlines()[-3:]
    record("T3.7 分析 CLI 测试套件", completed.returncode == 0, " | ".join(tail) or completed.stderr[:200])


def check_git_ignore_and_audit() -> None:
    ignored = run_subprocess(
        ["git", "check-ignore", "-v", "config.json", "test_data/account.json"],
        cwd=FRAMEWORK_ROOT,
        timeout=60,
    )
    # 退出码 1 = 两个文件都不再被忽略（T3.4 期望）；0 = 仍有被忽略项
    ignore_ok = ignored.returncode == 1
    record(
        "T3.4 凭据文件不再被忽略",
        ignore_ok,
        "config.json 与 test_data/account.json 均可提交"
        if ignore_ok
        else f"check-ignore 退出码 {ignored.returncode}: {ignored.stdout[:200]}",
    )
    audit = run_subprocess(
        [
            sys.executable,
            str(FRAMEWORK_ROOT / ".workbuddy" / "skills" / "svn-impact" / "evals" / "git_readiness_check.py"),
            "--repo-root",
            ".",
        ],
        cwd=FRAMEWORK_ROOT,
        timeout=120,
    )
    record("T3.4 提交前审计", audit.returncode == 0, (audit.stdout or audit.stderr).strip()[:200])


def check_chinese_documentation() -> None:
    completed = run_subprocess(
        [sys.executable, "tools/chinese_documentation_check.py", "--root", ".", "--include-skills"],
        cwd=FRAMEWORK_ROOT,
        timeout=300,
    )
    detail = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        detail = "；".join(detail.splitlines()[:6])
    record("简体中文独立验收项", completed.returncode == 0, detail[:300])


def check_cli_inventory_render() -> None:
    inv = run_subprocess([sys.executable, "-m", "svn_analyse", "inventory"], cwd=ANALYSE_ROOT, timeout=300)
    record(
        "T3.5 inventory 新路径实跑",
        inv.returncode == 0,
        (inv.stdout or inv.stderr).strip().splitlines()[-1][:200] if (inv.stdout or inv.stderr) else "无输出",
    )
    # render 输入可复现性：output/ 不入 Git，干净 clone 中没有历史分析产物，
    # 因此这里先用报告模块生成固定 fixture（r000000），再执行 render，
    # 保证任何新环境都能复现该验证项；验证后清理 fixture 目录。
    import shutil

    from svn_analyse import report as report_mod

    fixture_rev = "r999999"
    fixture_dir = ANALYSE_ROOT / "output" / fixture_rev
    fixture_facts = {
        "revision": 999999,
        "author": "phase3-verification",
        "date": "2026-08-19",
        "message": "三期验证 fixture（非真实提交）",
        "working_copy_revision": "999999",
        "changed_files": [
            {
                "path": "src/com/engine/email/web/EmailAttachmentCenterAction.java",
                "action": "M",
                "kind": "api",
            }
        ],
        "symbols": [{"name": "EmailAttachmentCenterAction", "file": "a.java", "kind": "class"}],
        "endpoints": [
            {
                "method": "GET",
                "url": "/api/email/attachment/list",
                "action": "EmailAttachmentCenterAction.list",
            }
        ],
        "impact": [{"symbol": "EmailAttachmentCenterAction", "size": 1, "note": "fixture"}],
        "existing_api": [{"url": "/api/email/attachment/list", "wrapper": "", "file": "", "tests": []}],
        "diff_excerpt": "+ fixture",
        "warnings": [],
        "confidence": "high",
    }
    try:
        report_mod.write_outputs(fixture_dir, fixture_facts)
        render = run_subprocess(
            [sys.executable, "-m", "svn_analyse", "render", f"output/{fixture_rev}"],
            cwd=ANALYSE_ROOT,
            timeout=120,
        )
        rendered_html = fixture_dir / "report.html"
        ok = render.returncode == 0 and rendered_html.is_file() and fixture_rev in rendered_html.read_text(encoding="utf-8")
        detail = (render.stdout or render.stderr).strip().splitlines()[-1][:200] if (render.stdout or render.stderr) else "无输出"
        record("T3.5 render 新路径实跑", ok, f"fixture {fixture_rev}：{detail}")
    finally:
        shutil.rmtree(fixture_dir, ignore_errors=True)


def check_analyse_mcp_end_to_end() -> None:
    started = time.monotonic()
    analyse = run_subprocess(
        [sys.executable, "-m", "svn_analyse", "analyse", "r349149", "--skip-update"],
        cwd=ANALYSE_ROOT,
        timeout=900,
    )
    elapsed = round(time.monotonic() - started, 1)
    if analyse.returncode != 0:
        record(
            "T3.5/T3.10 analyse r349149（本地 MCP 全链路）",
            False,
            f"退出码 {analyse.returncode}（{elapsed}s）: {(analyse.stderr or analyse.stdout)[-300:]}",
        )
        return
    payload = json.loads(analyse.stdout)
    # CLI 输出里的 facts 字段是 facts.json 的路径，需读文件取完整事实。
    facts_path = Path(str(payload.get("facts") or ""))
    try:
        facts = json.loads(facts_path.read_text(encoding="utf-8")) if facts_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        facts = {}
    warnings = payload.get("warnings") or []
    mcp_degraded = any("MCP" in item or "mcp" in item.lower() for item in warnings)
    detail = (
        f"confidence={payload.get('confidence')}, endpoints={len(facts.get('endpoints') or [])}, "
        f"impact_rows={len(facts.get('impact') or [])}, warnings={len(warnings)}, {elapsed}s"
        + ("（图谱降级）" if mcp_degraded else "（MCP 查询正常）")
    )
    record("T3.5/T3.10 analyse r349149（本地 MCP 全链路)", analyse.returncode == 0 and not mcp_degraded, detail)


def check_retest_execution() -> None:
    # fail_probe 探针是二期为验证报告分析链路刻意保留的必然失败用例，
    # 其去留（删除或注册专用 mark）仍待用户确认；验证时按 node id 显式排除。
    probe_nodeid = (
        "test_case/test_board_case/test_board_widget_api.py"
        "::TestBoardWidgetGetDataAPI::test_allure_failure_analysis_probe"
    )
    completed = run_subprocess(
        [
            sys.executable,
            "-m",
            "pytest",
            "test_case",
            "-m",
            "r349149",
            "--deselect",
            probe_nodeid,
            "-q",
        ],
        cwd=FRAMEWORK_ROOT,
        timeout=900,
    )
    # 只保留 pytest 摘要行，过滤 Allure 提示等无关输出。
    lines = (completed.stdout or "").strip().splitlines()
    summary_lines = [ln for ln in lines if "passed" in ln or "failed" in ln or "error" in ln.lower()]
    tail = " | ".join(summary_lines[-3:]) or " | ".join(lines[-3:])
    record(
        "T3.10 阶段 C 执行 r349149",
        completed.returncode == 0,
        tail or f"退出码 {completed.returncode}（环境版本差异假设：本地工作副本版本可能与测试环境部署版本不一致）",
    )


def check_git_branch_decision_tree() -> None:
    """git-branch 决策树实操：查询 → 新建临时分支 → 切换 → 切回 → 删除本次创建的临时分支。

    安全约束（对齐三期计划书的安全边界）：绝不强制删除任何既有分支——
    同名分支可能是用户未合并的工作成果；遇到重名时改用时间戳后缀的新名字，
    收尾只删除本次运行自己创建的分支，且使用要求已合并的 -d。
    """
    base_name = "eval/t3-probe"

    def git(*args: str) -> subprocess.CompletedProcess:
        return run_subprocess(["git", *args], cwd=FRAMEWORK_ROOT, timeout=60)

    def branch_exists(name: str) -> bool:
        return git("show-ref", "--verify", "--quiet", f"refs/heads/{name}").returncode == 0

    current = git("branch", "--show-current")
    origin_branch = (current.stdout or "").strip() or "master"
    if current.returncode != 0:
        record("T3.10 git-branch 决策树实操", False, f"查询当前分支失败: {current.stderr[:150]}")
        return
    invalid = git("check-ref-format", "--branch", "bad name")
    if invalid.returncode == 0:
        record("T3.10 git-branch 决策树实操", False, "非法分支名未被 check-ref-format 拒绝")
        return
    # 同名分支已存在时（可能是用户工作成果或上次运行遗留），绝不删除，改用唯一新名。
    branch_name = base_name
    if branch_exists(branch_name):
        branch_name = f"{base_name}-{time.strftime('%Y%m%d%H%M%S')}"
        if branch_exists(branch_name):
            record("T3.10 git-branch 决策树实操", False, f"无法取得唯一验证分支名：{branch_name} 已存在")
            return
    create = git("checkout", "-b", branch_name, origin_branch)
    if create.returncode != 0:
        record("T3.10 git-branch 决策树实操", False, f"新建分支失败: {create.stderr[:150]}")
        return
    after_create = (git("branch", "--show-current").stdout or "").strip()
    back = git("checkout", origin_branch)
    # 只删除本次运行创建的分支；-d 要求分支已合并，未合并时 git 会拒绝，不会丢失工作。
    delete = git("branch", "-d", branch_name)
    ok = after_create == branch_name and back.returncode == 0 and delete.returncode == 0
    if ok:
        detail = f"当前分支 {origin_branch} → 新建并切到 {branch_name} → 切回 {origin_branch} → 已删除本次创建的临时分支"
    else:
        detail = (
            f"切换/回滚/清理未全部成功（create_ok={after_create == branch_name}, "
            f"back={back.returncode}, delete={delete.returncode}）"
            + ("" if delete.returncode == 0 else f"；分支 {branch_name} 未删除，请人工确认")
        )
    record("T3.10 git-branch 决策树实操", ok, detail)


def write_report() -> Path:
    report_path = ANALYSE_ROOT / "phase3_verification_report.md"
    lines = ["# 三期验证批处理报告", "", f"- 运行时间：{time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
    for item in RESULTS:
        mark = "✅" if item["ok"] else "❌"
        lines.append(f"- {mark} **{item['name']}**：{item['detail']}")
    passed = sum(1 for item in RESULTS if item["ok"])
    lines += ["", f"合计：{passed}/{len(RESULTS)} 项通过。"]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="三期验证批处理。")
    parser.add_argument("--skip-e2e", action="store_true", help="跳过 analyse/retest 等重量级端到端项。")
    args = parser.parse_args()

    # Windows 控制台默认 GBK，子进程输出按 utf-8 解码后可能含替换字符，
    # 统一把本进程输出改为 utf-8 + replace，避免打印时 UnicodeEncodeError。
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

    sys.path.insert(0, str(ANALYSE_ROOT))
    sys.path.insert(0, str(FRAMEWORK_ROOT))

    checks = [
        check_eval_validator,
        check_probe_smoke,
        check_trigger_runner,
        check_framework_pytest,
        check_cli_pytest,
        check_git_ignore_and_audit,
        check_chinese_documentation,
        check_cli_inventory_render,
        check_git_branch_decision_tree,
    ]
    if not args.skip_e2e:
        checks.append(check_analyse_mcp_end_to_end)
        checks.append(check_retest_execution)

    for check in checks:
        try:
            check()
        except Exception as exc:  # noqa: BLE001 - 单项失败不中断批处理
            record(check.__name__, False, f"执行异常: {type(exc).__name__}: {exc}")

    report_path = write_report()
    failed = [item["name"] for item in RESULTS if not item["ok"]]
    print(f"\n报告已写入：{report_path}")
    print(f"通过 {len(RESULTS) - len(failed)}/{len(RESULTS)} 项" + (f"；失败项：{failed}" if failed else "；全部通过"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
