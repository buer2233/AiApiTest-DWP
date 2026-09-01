# 新人引导操作参考

## 每日记忆格式

文件名为 `.workbuddy/memory/onboarding-YYYY-MM-DD.md`，示例：

```text
date: 2026-08-31
status: completed
workspace: api-test-E9
branch: master_dwp
checks: python,pip,pytest,allure,codebase-memory,codebase-memory-ops
next: 使用 svn-impact 分析指定 revision
```

`status` 只能是 `completed`、`skipped` 或经确认后的 `reset`。写文件前创建目录，更新使用临时文件和原子替换。记忆目录已被 `.gitignore` 排除，提交前确认未出现在暂存区。

## 阻断处理表

| 阶段 | 现象 | 处理 |
|---|---|---|
| 权限/克隆 | 401、连接失败、目录缺项 | 保留错误信息，提示申请权限或联系开发人员；不继续分析 |
| 依赖 | pip 网络/权限/版本错误 | 指出失败包和修复命令，安装成功后重试 |
| MCP | 任一探针失败 | 联系开发人员处理；禁止用户自行改 MCP 配置，禁止本地替代查询 |
| 分支 | 当前为 master 或工作区脏 | 先切非 master；未提交改动必须由用户决定保留方式 |
| 配置 | 用户拒绝复用或字段无效 | 询问新值或暂停；不把账号写入代码/报告 |
| revision | 格式不合法 | 要求 `r` 加正整数或连续区间 |
| 功能审核 | 用户未确认定稿 | 停止代码修改，保留清单供反馈 |
| 造数 | 前置接口失败 | 阻断用例并记录原因、尝试、环境、建议 |
| 测试 | 用例失败 | 先声明部署版本差异，再做指纹归因 |
| Git | 未确认 push 或目标为 master | 只展示 readiness，拒绝远程写操作 |

## 完成判定

至少有一笔 revision 产出分析事实和设计、接口用例已执行、Allure 报告可经 HTTP 查看、测试摘要已展示；commit/push 是否执行必须单独记录用户确认结果。
