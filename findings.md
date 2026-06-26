# 前端目录清理发现记录

## 2026-06-26

- 仓库根目录不存在 `.codegraph/`，本次清理不使用 CodeGraph。
- 本次用户指令是明确清理 `front-end/` 目录，不涉及重新设计或实现前端功能。
- 需要保留的前端协作规则文件只有：
  - `front-end/AGENTS.md`
  - `front-end/CLAUDE.md`
- 首次删除后残留 `.vite/`、`node_modules/`、`.vite-dev.log`，原因是前端 Vite 开发服务仍在运行并锁定文件。
- 清理完成后，`front-end/` 目录只剩 `AGENTS.md` 与 `CLAUDE.md`。
