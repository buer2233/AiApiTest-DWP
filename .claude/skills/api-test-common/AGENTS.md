# api-test-common Skill 指南

本目录是 `ai-api-test` 的项目级 skill，固定位置为 `<project>/.claude/skills/api-test-common/`。

## 关键目录

- `SKILL.md`：入口说明，包含新增 / 维护分流。
- `doc/`：前置门禁、编码规范、新增三方式、维护四方式。
- `flow_chart/flow.md`：Mermaid 流程源文件；本通用版本不包含导出图片。
- `capture/`：mitmproxy 抓包脚本与抓包过滤配置。
- `tools/`：索引扫描、抓包匹配、抓包服务检查。
- `skill_utils/`：工具共享代码。

## 约束

- 项目根由 skill 位置向上三层推导。
- 项目根必须包含 `config.py` 和 `test_case/`。
- 抓包运行时产物写入 `<project>/runtime/`。
- 抓包允许前缀配置为 `capture/allowed_prefixes.txt`，文件为空时不限制；有内容时仅抓取匹配前缀的请求。
- 抓包禁止前缀配置为 `capture/blocked_prefixes.txt`，文件为空时不限制；有内容时排除匹配前缀的请求。
- `allowed_prefixes.txt` 优先级高于 `blocked_prefixes.txt`：先按允许前缀筛选，再按禁止前缀排除。
- 不绑定任何具体业务系统。

## 开发维护

- 修改 `SKILL.md` 时，同步检查 `README.md`、`doc/` 和 `flow_chart/flow.md`。
- 修改工具脚本后，至少运行 `python -m compileall -q .claude/skills/api-test-common`。
- 修改抓包、索引或匹配逻辑后，运行 `python -m pytest tests/test_capture_addon_prefixes.py tests/test_skill_tools.py`。
