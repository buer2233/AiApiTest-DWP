# api-test-common Skill

本 skill 用于在 `ai-api-test` 通用接口自动化框架中新增和维护接口方法与 pytest 用例。

优先阅读：

1. `SKILL.md`
2. 按任务类型读取 `doc/preflight_gates_new.md` 或 `doc/preflight_gates_maintenance.md`
3. `doc/coding_style_guide.md`
4. 选定方式对应的 `doc/mode_*.md`
5. 维护任务额外读取 `doc/maintenance_prompt_context.md`

工具脚本默认从 `<project>/.claude/skills/api-test-common/` 推导项目根，并使用 `<project>/runtime/` 保存抓包运行时文件。

抓包过滤配置位于 `capture/`：

- `allowed_prefixes.txt`：允许抓取的 URL 前缀，空文件表示不限制；有内容时仅抓取匹配前缀的请求。
- `blocked_prefixes.txt`：禁止抓取的 URL 前缀，空文件表示不限制；有内容时排除匹配前缀的请求。
- 过滤顺序为先应用 `allowed_prefixes.txt`，再应用 `blocked_prefixes.txt`。

维护方式4默认优先使用 `/test-fixing`；只有 `/test-fixing` 无法解决或需要调用栈/局部变量辅助定位时，才使用 `/Debugging`。
