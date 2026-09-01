# 纯前端改动的契约审视（阶段 A 例外规则）

当 `facts.json` 的 `pure_frontend` 为 `true` 时，默认不落接口用例。但有一种情况要额外审视：**前端改动改变了对某个既有接口返回数据的消费方式**。此时「改动的正确性」不再由被改动的代码自身决定，而是押在它所依赖的接口返回契约上——即使后端代码一行没动，后端返回结构一旦不满足前端新假设，前端就会静默取错值。给这个既有接口补一条**只读契约回归用例**，是守住该前提、在接口结构被误改时第一时间报警的低成本防御。

## 判定：什么算「改变接口消费方式」

命中以下任一，且能定位到具体既有接口，即触发例外：

- 取数方式改变（核心信号）：`Object.values(...)`/数组下标 → map 按 key 取值，或反向；数组/对象之间转换后再取值。
- 新增或收紧字段假设：前端开始依赖某个字段「必须是对象/数组/特定 key 结构」，或该字段为零值时前端会走分支/取错值。
- 新增显式展判断：如 `isShowValidity(key, map)` 依据接口返回的某 map 字段决定 UI 显隐。

不触发例外（保持纯前端、零接口用例）：

- 纯样式、文案、布局、动画、图标、CSS/class 调整。
- 组件内部状态管理的改动，不涉及后端响应数据消费方式的改变。
- 请求参数拼接调整但取值方式未依赖新契约（视情况归入普通功能用例即可）。

`.jsp` / `.ftl` / `WEB-INF/**` / 配置模板本身不算纯前端，不进入本规则。

## 执行步骤

1. 定位接口：在 diff 涉及的源码附近 grep 出 `WeaTools.callApi('/api/...')` 或等价请求封装，确认 method、URL、请求参数。
2. 核准契约：用只读方式实际调用一次该接口（走既有登录 fixture），确认返回结构确实满足前端新假设（如 `resourceValidityInfo` 确为 map 且 key 与密级 key 对应）。看不到返回时不编造结构。
3. 判断复用：跑 `cd E9_svn_analyse; python -m svn_analyse inventory` 读 `_inventory.json`，URL 已有封装则复用；没有则新建 `page_api/<模块名>_api/`。
4. 落一条契约用例：断言聚焦「前端新逻辑依赖的那个数据结构前提」，而非后端业务行为。典型断言：
   - 目标字段必须是 map（dict）而非数组；
   - map 的 key 与关联选项列表的 key 一一对应；
   - value 类型符合前端假设（如保密期限是字符串、可空但字段存在）。
5. 标记与结论：用例挂 `@pytest.mark.r<rev>`；`design.json` 的 `impact_summary` 保持「纯前端改动」，在 `api_cases` 里补一条说明「依赖接口契约回归」，报告结论注明「纯前端改动，仅补依赖接口契约回归」。

## 写作边界

- 只补**只读查询**接口的契约用例，避免触发写操作或依赖业务前置数据。
- 环境部署版本未确认时，用结构化断言（成功标志 + 数据结构存在）为通过标准；契约具体值用 `allure.attach` 记为信息性附件，不因环境落后误报失败。
- 不是把整棵调用树都列为回归范围；只盯「本次前端消费方式改变所直接踩中的那条接口契约」。

## 已落地范例

r349137（E9MM 公文改造）：`UploadFileComponent.js` 将密级→保密期限取值由 `Object.values(resourceValidityInfo)[secretLevel]` 改为 `validityInfo[secretLevel]`，并新增 `isShowValidity()` 依据 `needValidityInfo` map 控制「保密期限」显隐。对应补 `/api/odoc/odocFile/selectSecLevel` 的契约用例（`OdocFileAPI.select_sec_level`），断言 `resourceValidityInfo` 为 map 且 key 与密级选项一一对应。