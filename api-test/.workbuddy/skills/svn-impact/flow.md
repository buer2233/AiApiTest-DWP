# svn-impact 执行流程图

本文件是 `svn-impact` 的可视化流程基线。它与 `SKILL.md` 保持同一条执行契约：后续优化 SKILL 时，先更新流程图和节点说明，再同步修改文字规则与 Evals。单笔和批次都遵循同一条 A → A+ → A++ → B/前置数据 → C → 报告分析生命周期；批次只在阶段 A 增加 resolver、逐笔 worker 和 aggregate design。公共规则见 `references/common-analysis-contract.md`，功能用例设计仍统一引用 `references/functional-case-design.md`。

## 总流程

```mermaid
flowchart TD
    U[用户输入] --> R{识别意图}
    R -->|初始化/修改配置| CFG[读取 config.json 脱敏摘要]
    CFG --> CFGOK{配置完整且用户确认?}
    CFGOK -->|否| TMPL[返回一次性配置模板并等待填写]
    CFGOK -->|是| REV[收集一个正整数 revision]
    TMPL --> REV

    R -->|分析 rREV| A0[阶段 A: 校验单笔 revision]
    REV --> A0
    A0 --> A1[运维 MCP: e9_svn_log + e9_svn_diff]
    A1 --> A2[查询 MCP: search_graph + trace_path + get_code_snippet]
    A2 --> A3{纯前端改动?}
    A3 -->|是| A4[写 facts: pure_frontend=true]
    A4 --> A5[跳过 trace_path，生成界面功能用例]
    A5 --> A5B{前端改变了接口消费方式?}
    A5B -->|是| A5C[契约审视: 定位接口→核准契约→补只读契约用例]
    A5B -->|否| A5D[零接口用例，纯前端结论]
    A3 -->|否| A6[MCP search_graph + trace_path inbound]
    A6 --> A7[后端端点提取与诊断]
    A7 --> A8[前端操作反查: 页面/按钮/表单 → 事件 → 请求封装 → URL/方法/参数]
    A8 --> A9[合并后端调用链与前端操作证据]
    A9 --> A10[写 facts.json/design.json/report]
    A10 --> A11[render 生成 HTML/MD]
    A5C --> A11
    A5D --> A11
    A11 --> STOPA[回复报告路径和下一句口令，等待确认]

    R -->|分析 revision 集合/区间| BA0[批次解析：校验 2–10 笔与 batch_message]
    BA0 --> BA1[读取 E9 信息 MCP：A/B 邻域解析实际集合]
    BA1 --> BA2{resolver 完整?}
    BA2 -->|否| BA3[输出真实阻断原因与修改模板]
    BA2 -->|是| BA4[逐 revision 调用单笔分析 worker（每笔最多 3 次 attempt）]
    BA4 --> BA5{全部关键事实完整?}
    BA5 -->|否| BA6[写部分审计报告，stage_b_gate=false，阻断接口代码]
    BA5 -->|是| BA7[聚合 facts/design/reverse_lookup，保留 source_revisions]
    BA7 --> A11
    BA6 --> STOPA

    A11 --> FC0[阶段 A+: 功能用例设计]
    FC0 --> FC1[读 facts/reverse_lookup → 变更行为点 + 影响面调用方]
    FC1 --> FC2[按 functional-case-design.md 设计: CRUD/边界值/等价类/异常/组合/权限状态]
    FC2 --> FC3[写 functional_test_cases.md，不落自动化代码]
    FC3 --> RV0[阶段 A++: 人工审核]
    RV0 --> RV1[呈现清单供人工审核]
    RV1 --> RV2{人工反馈?}
    RV2 -->|需修改| RV3[就地修改清单并重呈现改动点]
    RV3 --> RV1
    RV2 -->|确认定稿| STOPB[回复已定稿 + 下一句口令 按方案实现接口自动化，等待确认]

    R -->|按方案实现接口自动化| B0[阶段 B: 读取 design + reverse_lookup + inventory + 定稿功能用例]
    STOPB --> B0
    B0 --> BPR{功能用例已人工定稿?}
    BPR -->|否| RV0
    BPR -->|是| BM{endpoint_diagnostics 需人工复核?}
    BM -->|是| BMX[输出候选入口清单，阻塞等待人工复核]
    BM -->|否| B1{URL 已有封装?}
    B1 -->|是| B2[复用封装，只追加用例和 revision mark]
    B1 -->|否| B3[创建模块 API 封装]
    B2 --> D0{用例需要业务前置数据?}
    B3 --> D0
    D0 -->|否| C0[阶段 C 执行 pytest]
    D0 -->|是| D1[读取 reverse_lookup.json + 前端操作证据]
    D1 --> D2[先用业务接口查询当前环境数据]
    D2 --> D3{命中且状态/权限满足?}
    D3 -->|是| D4[复用业务 ID 并绑定用例]
    D3 -->|否| D5[生成数据计划: 查询 → 创建 → 配置 → 验证]
    D5 --> D6{已有状态基线可复用?}
    D6 -->|是| D7[test_data_runner status 校验并用接口验证对象]
    D6 -->|否| D8[test_data_runner build 幂等构建 prepare_<module>_test_data.py]
    D8 --> D9[写 test_data/<module>/<module>_test_data.json + 受管字段 + 敏感门禁]
    D7 --> D10[批量环境探针与前后版本对比]
    D9 --> D10
    D4 --> D10
    D10 --> D11{环境未部署目标 revision?}
    D11 -->|是| D12[保留成功标志断言，行为差异作为信息性证据]
    D11 -->|否| D13[启用行为级断言]
    D12 --> C0
    D13 --> C0
    C0 --> C1[Allure 原始结果 + 阶段 Trace]
    C1 --> C2{有 failed/broken?}
    C2 -->|否| C3[生成报告，回复无失败用例]
    C2 -->|是| E0[冻结脱敏 manifest]
    E0 --> E1[按失败指纹分片只读分析]
    E1 --> E2[主会话校验 SHA/敏感信息/指纹]
    E2 --> E3[原子回写唯一 AI 分析附件]
    E3 --> E4[allure generate + summary]
    E4 --> E5[回复原因、证据、建议和环境版本前提]
    C3 --> SRV[服务报告目录，交付 http 链接]
    E5 --> SRV

    R -->|复测 rREV| C0
    R -->|分析测试报告| E0
    R -->|接口覆盖/按关键词选例| Q0[查询 sqlite3 inventory + revision_meta/test_methods]
    Q0 --> Q1{需要 MCP 反查?}
    Q1 -->|是| A6
    Q1 -->|否| Q2[输出封装/用例清单]

    SAFE[全程安全门禁: 不丢失未提交变更、不删除既有分支、不写凭据] -.-> A0
    SAFE -.-> D5
    SAFE -.-> E3
```

## 节点说明

| 节点 | 关键规则 | 失败处理 |
|------|----------|----------|
| 阶段 A | 单笔取一个正整数 revision；批次先由 resolver 解析实际 revision 集合，再逐笔调用同一个 worker。第一步 `e9_svn_log` + `e9_svn_diff`，结构查询走 `search_graph` + `trace_path`；不执行本地 SVN，不用 `detect_changes` / `impact` / `callers` | MCP 失败写警告，不编造事实；批次按 revision 重试，最终缺事实则阻断 B |
| 批次聚合 | 逐笔 facts/design/reverse_lookup 完成后再合并文件、符号、端点、影响模块和用例候选，保留 `source_revisions`；聚合后仍进入同一 A+ / A++ / B / C | resolver 不完整或任一关键事实缺失时只生成审计报告，`stage_b_gate=false` |
| 契约审视 | 纯前端但改变了接口消费方式时，定位接口、实核准契约、补只读契约用例；详见 `references/pure-frontend-contract.md` | 看不到返回结构不编造；URL 已有封装则复用 |
| 阶段 A+ 功能用例设计 | 单笔和批次统一按 `references/functional-case-design.md` 设计；批次先合并联合影响面，再覆盖所有受影响模块；前置数据先查询并复用，确认缺失后**能自动造则自动造、能拆多步则拆多步**；产出 `functional_test_cases.md`；不落自动化代码 | 缺事实/接口证据时不编造，标注「图谱未覆盖」 |
| 阶段 A++ 人工审核 | 呈现清单 → 反馈 → 就地修改 → 再确认，循环至人工定稿；未经定稿不进入阶段 B | 中途换 revision/回阶段 A 按触发词重入，不强行推进 |
| 阶段 B | URL 已封装则复用；从定稿功能用例抽「非 manual」条目落接口用例并标注来源 FC 编号；新增用例前读取后端与前端证据 | 无证据不得凭猜测生成接口或断言；端点需人工复核时阻塞 |
| 后端反查 | `search_graph` + `trace_path(inbound)` 查询变更符号、入口和调用方；端点为空必须输出诊断 | 记录候选入口和人工复核，不静默判空 |
| 前端反查 | 扫描页面、菜单、按钮、表单、事件处理器、请求封装和 URL；必要时用浏览器 Network/Har 运行证据校正静态结果 | 动态拼接无法解析时标记 `needs_runtime_trace` |
| 阶段 B | URL 已封装则复用；新增用例前读取后端与前端证据（reverse_lookup.json） | 无证据不得凭猜测生成接口或断言；端点需人工复核时阻塞 |
| 前置数据 | 先用业务接口查询并复用当前环境数据；确认缺失后生成计划、幂等构建、状态文件和 cleanup；经 test_data_runner 过敏感门禁，输出只含业务标识 | 造数失败按四项格式阻塞；代码完成但运行时仍缺数据时才安全跳过，不索要内部 ID |
| 阶段 C | 环境 revision 未确认时使用结构化成功断言，行为差异写 Allure 信息附件 | 不把环境版本差异定性为产品缺陷 |
| 报告分析 | 先冻结 manifest，再分片分析，主会话唯一回写 | SHA 变化或出现敏感信息时停止回写 |
| Allure 报告查看 | 交付前起本地 HTTP 服务（`python -m http.server 8917`），以 http 链接打开，禁 file:// | Git Bash 下 allure fork 失败改用 PowerShell 调 allure.bat；端口占用换空闲端口 |
| Git/文件安全 | 分支操作保护既有引用；清理只作用于可再生产物 | 失败回滚原状态并保留用户变更 |

## 分支与交付流程

Git 分支操作由同级 `git-branch` SKILL 负责；`svn-impact` 只在实现和交付边界调用它，不直接静默切换或删除分支。

```mermaid
flowchart LR
    G0[用户请求切换/新建分支] --> G1[读取 git.default_branch]
    G1 --> G2[git status --porcelain]
    G2 --> G3{有未提交变更?}
    G3 -->|是| G4[询问 stash/保留/取消]
    G4 -->|取消| GX[零改动结束]
    G4 -->|继续| G5[校验分支名 check-ref-format]
    G3 -->|否| G5
    G5 --> G6{目标分支已存在?}
    G6 -->|是| G7[切换并验证当前分支]
    G6 -->|否| G8[询问是否从默认分支新建]
    G8 -->|否| GX
    G8 -->|是| G9[fetch 默认分支 + checkout -b]
    G7 --> G10[失败则回滚原分支]
    G9 --> G10
    G10 --> G11[实现阶段提交前定向 git readiness 检查]
    G11 --> G12{审计通过?}
    G12 -->|否| G13[修复阻断项，不提交]
    G12 -->|是| G14[询问用户确认后定向提交/推送]
```

交付清单只暂存本次 `page_api/`、`test_case/`、`tools/`、`test_data/`、`.workbuddy/`、`E9_svn_analyse/` 和必要文档；不使用宽泛 `git add .`。远端开发 R1-R5 不得在本地四期未验收时启动。

## 前端操作证据格式

前端反查结果写入 `facts.json` 的 `frontend_operations`（四期起由 `analyse` 自动产出），每条至少包含：

```json
{
  "operation": "文档下载",
  "page": "相对页面路径或路由",
  "trigger": "按钮/菜单/表单提交及事件函数",
  "request": {"method": "POST", "url": "/api/..."},
  "parameters": ["字段名"],
  "response_effect": "页面状态或下载结果",
  "evidence": {"source": "static_scan", "file": "相对文件", "line": 12, "matched": "命中片段"},
  "confidence": "static|runtime|confirmed|conflict"
}
```

`confidence` 只能取 `static`、`runtime`、`confirmed`、`conflict` 四个值。静态扫描未命中的端点不伪造证据，记入 `reverse_lookup.json` 的 `frontend_scan.misses`，标注需浏览器 Network/HAR 运行时证据。当静态 URL 与运行时 Network 记录不一致时，保留两份证据并标记 `conflict`，不能自动选择一个"看起来正确"的地址。
