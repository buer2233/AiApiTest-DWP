# 开发 Loop 轻量化重构 Stage14 盘点发现

## 可用性口径

当前会话注入的 `Skills` 清单是可调用能力的唯一事实来源。磁盘目录扫描仅用于识别残留，不得据此调用未注入会话的 Skill。

## 当前会话可用 Skills

| 分类 | Skills |
| --- | --- |
| 位图与设计 | `imagegen`、`design-system`、`ui-ux-pro-max` |
| 图表与架构 | `drawio-skill` |
| Python | `python-testing`、`Debugging` |
| OpenAI / 扩展管理 | `openai-docs`、`plugin-creator`、`skill-installer`、`find-skills` |
| Skill 开发 | `skill-creator`（当前存在两个同名来源，使用时必须以会话实际选中项为准） |

## 磁盘存在但当前会话未暴露

`review-agent`、`grill-me`、`loop-me`。这些目录不能写成当前会话可用 Skill，也不能作为独立审查门禁的依赖。

## 生效治理文档中的失效引用

- 全局：`using-superpowers`、`planning-with-files`、`brainstorming`、`product-requirements`、`test-driven-development`、`systematic-debugging`、`receiving-code-review`、`subagent-driven-development`。
- 后端：`django-tdd`、`api-design`、`python-patterns`、`security-review`。
- 前端：`vue-best-practices`、`frontend-design`、`vue-router-best-practices`、`vue-pinia-best-practices`、`vue-testing-best-practices`、`vue-debug-guides`。
- 测试与 UI：`test-cases`、`prototype-prompt-generator`、`ckm:design-system`。

## 重构结论

1. 不再维护全局强制 Skill 组合。
2. Skill 只做匹配任务的可选增强，不能替代阶段输入、产物或质量门禁。
3. 把需求深挖、测试覆盖、API 设计、诊断、Vue 工程实践和独立审查直接写成行为规则。
4. 保留当前可用 Skill 的场景化索引，但明确清单会随会话变化。
