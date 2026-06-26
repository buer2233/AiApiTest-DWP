# 前端目录清理任务计划

## 目标

清理 `front-end/` 目录中除 `AGENTS.md` 和 `CLAUDE.md` 之外的全部前端代码、依赖目录与运行产物，为后续重新规范开发流程做准备。

## 范围

- 删除范围：`front-end/` 目录内除 `AGENTS.md`、`CLAUDE.md` 之外的所有文件和目录。
- 明确包含：`front-end/node_modules`。
- 保留范围：`front-end/AGENTS.md`、`front-end/CLAUDE.md`。
- 禁止范围：不清理仓库其它模块，不删除根目录计划文件和项目文档。

## 步骤

| 步骤 | 状态 | 说明 |
| --- | --- | --- |
| 确认前端目录和保留文件 | 完成 | 核对目录存在且保留文件在目标目录内 |
| 记录清理计划和边界 | 完成 | 已在本文件中明确删除和保留范围 |
| 执行受限清理 | 完成 | 已删除全部非保留条目，包括 `node_modules` |
| 验证清理结果 | 完成 | 已确认只剩 `AGENTS.md` 与 `CLAUDE.md` |

## 错误记录

| 错误 | 处理 |
| --- | --- |
| `using-superpowers` 初始系统路径不存在 | 改用实际路径 `C:\Users\admin\.codex\skills\using-superpowers\SKILL.md` 成功读取 |
| `Remove-Item` 删除 `node_modules` 和 `.vite-dev.log` 时被占用 | 定位到 `front-end` 下仍在运行的 Vite 开发服务，准备结束相关进程后重试 |
| 首次结束进程命令匹配到当前 PowerShell 清理进程 | 改用更窄的 Vite/Node 进程匹配条件，确认无残留前端开发进程后继续删除 |
