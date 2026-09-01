# 阶段 B 前置数据决策树（四期 T4.4）

> 本文件是 `svn-impact` 阶段 B「按方案实现接口自动化」中前置数据分支的执行契约。
> 依赖四期 T4.1 端点诊断、T4.2 反查证据包与 T4.3 数据计划/运行器。
> 修改本文件时同步更新 `SKILL.md`、`flow.md` 与 `evals/workflow_eval_set.json`。
> 所有模块先遵守 `../functional-to-api-test/references/test-data-reuse.md`：查询当前环境并复用，确认缺失后才尝试造数。

## 0. 进入条件

阶段 B 开始时依次读取：

1. `E9_svn_analyse/output/r<rev>/design.json`（含 `reverse_lookup` 引用字段）；
2. `E9_svn_analyse/output/r<rev>/reverse_lookup.json`（入口、调用链、参数契约、前端操作证据、覆盖一致性）；
3. `E9_svn_analyse/output/_inventory.json`（已有封装/用例）。

## 1. 决策树

```text
读取 reverse_lookup.json
├─ endpoint_diagnostics.needs_manual_review = true（端点为空）
│    → 不生成接口用例；向用户输出候选入口清单与人工复核请求，阻塞等待
├─ entries 非空
│    ├─ coverage_consistency = covered_by_wrapper / covered_by_test
│    │    → 复用封装，仅追加用例与 revision mark
│    └─ uncovered
│         → 新建封装与用例；再判断用例是否依赖业务前置数据：
│            ├─ 不依赖（纯查询/无状态接口）→ 直接进入阶段 C
│            └─ 依赖 → 进入前置数据分支（见下）
└─ pure_frontend = true
     → 不触发任何数据构建，仅界面功能用例
```

### 前置数据分支

```text
读取 reverse_lookup + 前端操作证据
├─ 先用现有接口按业务条件查询当前测试环境？
│    ├─ 命中且状态/权限满足 → 复用返回业务 ID，绑定用例
│    └─ 空或不满足 → 记录缺失对象，继续检查可审计基线
├─ test_data/<module>/ 已有状态基线？
│    ├─ 有 → python -m tools.test_data_runner status --module <module>
│    │       ├─ ready=true → 仍需用接口验证基线对象存在且满足条件，再复用
│    │       └─ ready=false → 转「执行构建」
│    └─ 无 → 生成数据计划：按 reverse_lookup 的 entries/contracts 写
│            test_data/<module>/<module>_data_plan.json（查询→创建→配置→验证），
│            实现或复用 prepare_<module>_test_data.py，并在 MODULE_REGISTRY 登记
├─ 确认环境无可复用数据后，执行构建：python -m tools.test_data_runner build --module <module>
│    ├─ 成功 → 写入基线（含受管字段）→ 绑定用例
│    └─ 失败 → 按四项失败格式阻塞：缺失数据、已做查询/反查/造数尝试、真实失败原因、
│             人工准备内容和继续条件；不向用户索要内部 ID
└─ 构建后敏感门禁由运行器自动执行，失败即停止
```

## 2. 四类异常的分别处理

| 异常 | 判定依据 | 处理 |
|------|----------|------|
| 端点为空 | `endpoint_diagnostics.needs_manual_review=true` | 阻塞：给出候选入口与复核清单；不生成看似完整的接口用例 |
| 参数不明 | contracts 缺参数，或 frontend_scan.misses 标注动态拼接 | 降置信度；协议层断言先行，行为断言标注待运行证据/人工确认 |
| 数据缺失 | 现有接口查询无匹配，且 `status` 返回 ready=false、build 失败 | 四项失败格式阻塞；代码已完成但运行时仍缺数据时才显式 `pytest.skip` |
| 环境版本不一致 | 状态文件 `env_deployed_fixed=false` 或探测呈修复前特征 | P0 用结构化成功断言；行为差异写信息性附件；不定性产品缺陷 |

## 3. 硬门槛

- 前端操作、接口契约、行为预期任一项没有 `confirmed` 证据时，SKILL 必须降低置信度，
  禁止输出只会通过的假阴性用例；
- 业务数据一律先通过接口查询并复用，确认缺失后才自动构建或复用经接口验证的基线，**不得向用户索要组件 ID、文档 ID、流程实例 ID 等内部标识**；
- 纯前端提交或无接口变更的提交不触发数据构建。

## 4. 命令速查

```powershell
cd E9_svn_analyse; python -m svn_analyse reverse-lookup r<rev>
cd E9_svn_analyse; python -m svn_analyse reverse-lookup r<rev> --symbol <符号>
python -m tools.test_data_runner list
python -m tools.test_data_runner status --module <module>
python -m tools.test_data_runner build --module <module>
python -m tools.test_data_runner cleanup --module <module>
```
