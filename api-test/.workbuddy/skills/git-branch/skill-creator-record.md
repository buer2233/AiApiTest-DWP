# git-branch SKILL 创建记录（skill-creator）

- 创建日期：2026-08-19
- 创建方式：按 `skill-creator` 技能流程创建（意图确认 → SKILL.md 起草 → 触发/工作流评估集 → 迭代）。
- 对应需求：三期需求 7 · Git 分支管理 SKILL（`docs/三期开发/E9三期开发计划书.md` T3.2/T3.3）。

## 意图与范围

- 能力：自然语言切换 / 新建 api-test-E9 仓库分支；默认分支读 `config.json` 的 `git.default_branch`；新分支一律从默认分支拉取。
- 触发词：`切分支`、`切换分支`、`切换分支到 xxx`、`切到 xxx`、`新建分支`、`创建分支`、`git 分支`。
- 明确不做：push、merge、rebase、reset、删除分支等写操作；不触碰凭据字段。

## 决策树（四分支）

1. 解析目标分支名，省略 → 回退默认分支。
2. 未提交变更非空 → 询问（stash / 放弃 / 取消），绝不静默丢弃。
3. 分支已存在 → checkout；失败回滚原分支。
4. 不存在 → 确认「是否从默认分支新建」；确认则 fetch + checkout -b，否定则零改动。

## 安全边界

- `git check-ref-format --branch` 校验分支名，拒绝非法 / 空格 / 中文名。
- 只读操作（列分支、看当前分支）零副作用。
- 只读 `config.json` 的 `git` 块，缺省回退 `master` / `origin`；不读取、不输出账号密码。

## 评估资产（T3.3）

- `evals/trigger_eval_set.json`：触发集，正例 ≥11、负例 ≥7。
- `evals/workflow_eval_set.json`：工作流契约集，覆盖四分支 + 安全边界。
- `evals/validate_eval_set.py`：静态校验器（schema、唯一 ID、类别齐全、must_read 存在）。
- `evals/trigger-eval/run_trigger_eval_win.py`：Windows 触发评估 runner（检查点续跑、INCONCLUSIVE 隔离）。
- `evals/trigger-eval/skill_probe.py`：可运行技能探针，对每条查询给出明确的 triggered 判定，保证 accuracy 数值可复现（吸取一期 T1.6 全 INCONCLUSIVE 教训）。
