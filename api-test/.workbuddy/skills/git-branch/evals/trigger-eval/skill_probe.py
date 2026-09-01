#!/usr/bin/env python3
"""git-branch 技能触发探针。

对每条查询给出明确的 triggered 判定（JSON 行输出），用于触发成功率评估。
吸取一期 T1.6「探针无信号、全部 INCONCLUSIVE」教训：本探针任何情况下都
产出明确结论，保证 accuracy 数值可复现。

两种模式：
- rules（默认）：确定性规则匹配，实现 SKILL.md 文档化的触发词表与负向
  守卫，结果完全可复现，衡量「文档触发词表对自然语料的覆盖与拒识」。
- claude：调用 `claude -p` 无头探针做真实模型触发判定（需要 claude CLI
  可用），衡量模型侧的实际触发行为。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


SKILL_NAME = "git-branch"

# 负向守卫：命中即判不触发。这些说法与分支操作相邻但属于其他技能或流程，
# 必须先于正向词表判断，避免「切换」「新建」等动词造成误触发。
NEGATIVE_GUARDS = [
    re.compile(r"快速测试"),
    re.compile(r"分析测试报告|测试报告"),
    re.compile(r"按方案实现|实现接口自动化"),
    re.compile(r"(切换|切到|换到|修改).{0,8}(测试环境|环境|账号|配置)"),
    re.compile(r"更新代码|更新\s*svn|svn\s*update", re.IGNORECASE),
    re.compile(r"提交到|推送到|git\s+push", re.IGNORECASE),
    re.compile(r"^\s*r\d+\s*$", re.IGNORECASE),
    re.compile(r"分析\s*r\d+", re.IGNORECASE),
    re.compile(r"(新写|编写|补充|新增).{0,12}用例"),
]

# 正向触发词表：与 SKILL.md「触发词」节一致（7 类触发词 + 同义说法）。
POSITIVE_PATTERNS = [
    re.compile(r"切分支|切换分支"),
    re.compile(r"(切换|换|切)到.{0,16}分支"),
    re.compile(r"切到\s*[A-Za-z0-9_./-]+"),
    re.compile(r"回到.{0,8}(主分支|默认分支|master)", re.IGNORECASE),
    re.compile(r"(新建|创建|拉|建).{0,10}分支"),
    re.compile(r"分支.{0,6}(新建|创建)"),
    re.compile(r"git\s*分支", re.IGNORECASE),
    re.compile(r"(换|切)一?个分支"),
    re.compile(r"(当前|哪个|现在|在).{0,8}分支.{0,4}(上|吗|呢)?$"),
]


def decide_by_rules(query: str) -> tuple[bool, str]:
    """确定性规则判定：守卫优先，其次正向词表，默认不触发。"""
    text = query.strip()
    for pattern in NEGATIVE_GUARDS:
        if pattern.search(text):
            return False, f"guard:{pattern.pattern}"
    for pattern in POSITIVE_PATTERNS:
        if pattern.search(text):
            return True, f"rule:{pattern.pattern}"
    return False, "no_branch_signal"


CLAUDE_WRAPPER = (
    "你是技能触发判定器。判断下面的用户消息是否应当触发 git-branch 技能"
    "（该技能用自然语言切换或新建 api-test-E9 仓库的 Git 分支，触发词包括"
    "切分支、切换分支、切到 xxx、新建分支、创建分支、git 分支等；分析提交、"
    "执行测试、改配置、查报告等请求不触发）。只输出一行 JSON，形如 "
    '{"triggered": true} 或 {"triggered": false}，不要输出任何其他内容。\n'
    "用户消息："
)


def decide_by_claude(query: str, timeout: int) -> tuple[bool, str]:
    """调用 claude -p 做真实模型触发判定；不可用时明确报错。"""
    try:
        completed = subprocess.run(
            ["claude", "-p", CLAUDE_WRAPPER + query],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return False, "claude_cli_unavailable"
    except subprocess.TimeoutExpired:
        return False, "claude_probe_timeout"
    for line in completed.stdout.splitlines():
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload.get("triggered"), bool):
            return payload["triggered"], "claude_judgement"
    return False, f"claude_no_signal_exit_{completed.returncode}"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    parser = argparse.ArgumentParser(description="git-branch 技能触发探针。")
    parser.add_argument("query", help="待判定的用户消息。")
    parser.add_argument(
        "--mode",
        choices=("rules", "claude"),
        default="rules",
        help="判定模式：rules 为确定性规则匹配，claude 为无头模型实测。",
    )
    parser.add_argument("--timeout", type=int, default=90, help="claude 模式超时秒数。")
    args = parser.parse_args()

    if args.mode == "claude":
        triggered, detail = decide_by_claude(args.query, args.timeout)
    else:
        triggered, detail = decide_by_rules(args.query)
    print(json.dumps({"triggered": triggered, "detail": detail, "skill": SKILL_NAME}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
