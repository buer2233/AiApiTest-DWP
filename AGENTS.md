# AGENTS.md

本项目是一个用于使用 AI 编写和维护接口自动化测试用例的通用接口自动化框架，不绑定任何具体业务系统。所有新增和维护的接口自动化内容应保持可迁移、可复用，避免引入特定网站的登录流程、账号、cookie、token 或业务常量。

## 工作方式

**强制使用的 Skill**：新增或维护接口自动化用例时，必须强制使用 `.claude/skills/api-test-common/SKILL.md`，不得跳过该 skill 的流程。

**必须遵守的编码规范**：编写、修改、补齐、迁移或维护任何接口方法、pytest 用例前，必须先读取并遵守 `.claude/skills/api-test-common/doc/coding_style_guide.md`。

1. 先在 `test_case/page_api/` 编写接口方法。
2. 再在 `test_case/test_*_case/` 编写 pytest 用例调用接口方法。
3. 用例报告统一使用 Allure。
4. 抓包数据统一落在 `runtime/`。
5. `test_data/` 初始为空，需要时再放项目自己的测试数据。
6. 取值方法：多层取值优先用 `get_value()`，单层取值优先用 `.get()`。

## Skill

项目内置接口自动化编写 skill：

- 路径：`.claude/skills/api-test-common/SKILL.md`
- 使用要求：新增、修改、补齐、迁移或维护接口方法、pytest 用例时必须强制使用。
- 用途：按抓包、参考已有用例、cURL 三种方式生成和维护接口方法、pytest 用例。
- 注意：Allure 字段默认自动生成；`feature` 可由用户指定，也可根据抓包接口总结。

## 项目结构

```text
ai-api-test/
├── .claude/
│   └── skills/
│       └── api-test-common/
│           ├── SKILL.md                         # 强制使用的接口自动化新增/维护 skill
│           └── doc/
│               └── coding_style_guide.md        # 接口方法和 pytest 用例编码规范
├── config.py                                    # 模块级通用配置，base_url 必须包含协议和域名
├── conftest.py                                  # pytest 命令行参数和公共 fixture
├── runpytest.py                                 # 统一执行入口，负责 pytest 运行和 Allure 报告生成
├── test_case/
│   ├── page_api/                                # 接口方法封装层
│   │   └── public/
│   │       └── base_api.py                      # 接口请求基类
│   └── test_*_case/                             # pytest 接口用例层
├── test_data/                                   # 测试数据目录，初始为空，按项目需要添加
├── utils/                                       # 通用请求增强、日志、辅助能力
├── runtime/                                     # 抓包运行时产物，如 latest.jsonl、capture_selection.md
└── report/                                      # Allure 原始结果与 HTML 报告产物
```

## 运行命令

- 运行全部接口用例：`python runpytest.py`
- 指定用例目录：`python runpytest.py --case-path test_case/test_demo_case`
- 指定 marker：`python runpytest.py -m smoke`
- 清理旧 Allure 结果：`python runpytest.py --clean`
- 生成后打开报告：`python runpytest.py --open-report`

## AI 协作规则

- 默认使用简体中文沟通。
- 不提交真实账号密码、token、cookie、租户密钥或敏感地址。
- 报告、日志、抓包运行时产物不要作为业务代码提交。

## 减少常见 LLM 编码错误的行为准则
可根据项目特定需求合并使用： @andrej-karpathy-skills.md
