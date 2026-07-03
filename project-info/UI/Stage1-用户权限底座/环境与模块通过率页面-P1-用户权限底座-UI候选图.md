# 环境与模块通过率页面-P1-用户权限底座-UI候选图

## 元信息

| 项 | 内容 |
| --- | --- |
| 需求名 | 环境与模块通过率页面-P1-用户权限底座 |
| 候选范围 | 登录页、邀请码注册页、Cookie 授权门禁、401 未授权反馈 |
| 生成方式 | Codex `imagegen` 内置图片生成 |
| 生成日期 | 2026-07-03 |
| 当前状态 | 已选择候选图 5 作为 Figma 实际原型输入 |

## 设计基线

- 严格沿用仓库 `DESIGN-claude.md`：warm cream canvas、coral primary、dark product surface、warm ink text、hairline border、8px 主控件圆角和编辑式排版。
- 不展示真实账号、密码、token、Cookie、生产 URL 或敏感地址。
- Cookie 认证只抽象展示 `authToken Cookie`、脱敏星号和 401 门禁，不记录主人示例中的真实 Cookie。
- 登录与注册都必须体现：未授权 URL/API 访问被拦截，接口缺少有效授权 Cookie 时返回 401。

## 候选图

| 编号 | 方向 | 图片路径 | 适合场景 | 主要取舍 |
| --- | --- | --- | --- | --- |
| 1 | Execution Cockpit Gateway | `project-info/UI/Stage1-用户权限底座/环境与模块通过率页面-P1-用户权限底座-login-option-1-execution-cockpit.png` | 登录即进入执行指挥台，强调平台的数据和 Jenkins 能力 | 登录清晰，执行看板很强；注册入口较轻 |
| 2 | Invitation Ledger | `project-info/UI/Stage1-用户权限底座/环境与模块通过率页面-P1-用户权限底座-login-option-2-invitation-ledger.png` | 强调邀请码生命周期、一次性展示和 Cookie 鉴权规则 | 注册治理表达最好；登录态视觉相对弱 |
| 3 | Terminal Lock | `project-info/UI/Stage1-用户权限底座/环境与模块通过率页面-P1-用户权限底座-login-option-3-terminal-lock.png` | 强调技术可信、Route Guard、API 401 和 Cookie 校验 | 工程感最强；对普通成员略偏技术化 |
| 4 | Report Grid Entry | `project-info/UI/Stage1-用户权限底座/环境与模块通过率页面-P1-用户权限底座-login-option-4-report-grid-entry.png` | 登录页提前预览环境通过率、模块通过率和失败用例数据 | 与父需求页面连接最强；首屏信息量最大 |
| 5 | Access Split Gate | `project-info/UI/Stage1-用户权限底座/环境与模块通过率页面-P1-用户权限底座-login-option-5-access-split-gate.png` | 登录与邀请码注册并重，角色权限和受保护路由一屏说明 | P1 范围覆盖最完整；版式较规整、适合转 Figma |

## 人工校准结论

- 5 张候选图均满足 Claude 风格基线和企业测试平台定位。
- 候选图中的 token、Cookie、接口路径均为脱敏示意，不作为真实实现字段值。
- 主人已选择候选图 5 `Access Split Gate` 作为后续 Figma 原型方向。后续 Figma 原型需在该方向上补齐：
  - 登录默认态、登录失败态、登录提交中、登录成功跳转。
  - 邀请码注册默认态、邀请码无效、邀请码过期、注册成功。
  - 未登录直达受保护 URL 的重定向或 401 页面反馈。
  - 管理人员与普通成员的菜单和按钮权限差异。
  - 移动端或窄屏响应式布局。

## 主人选择记录

- [ ] 选择候选图 1
- [ ] 选择候选图 2
- [ ] 选择候选图 3
- [ ] 选择候选图 4
- [x] 选择候选图 5

选择时间：2026-07-03
