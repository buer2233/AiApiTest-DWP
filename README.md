# ai-api-test

`ai-api-test` 是一个面向 AI 协作的通用接口自动化测试框架。它不是把接口测试做成一个固定平台，而是把 AI、抓包数据、pytest、requests 和 Allure 组合成一套可复制、可二次开发、可直接落地到真实项目中的接口自动化工程模板。

项目内置 `.claude/skills/api-test-common`，用于指导 AI 按统一规范新增和维护接口方法、pytest 用例、Allure 报告和抓包生成流程。你可以把它复制到任意 Web 项目中，让 AI 基于真实请求快速生成可运行、可维护的接口自动化用例。

当前用例编写的SKILL引用自：https://github.com/buer2233/api-test-dwp

## 项目特点

- **AI 参与编写和维护**：内置接口自动化专用 skill，让 AI 按统一流程生成接口方法和测试用例。
- **不依赖接口文档**：支持通过抓包数据生成用例，接口路径、参数、请求头和真实响应都来自实际业务操作。
- **两层结构清晰**：`page_api` 负责接口方法封装，`test_*_case` 负责 pytest 用例和业务断言。
- **开箱即用**：基于 pytest、requests、Allure，保留 Python 项目的灵活性。
- **适合持续演进**：新增、补齐、迁移、维护用例都可以继续交给 AI 按项目规范处理。

## 为什么选择这个框架

### 对比传统接口自动化框架

传统接口自动化通常需要人工查看接口文档、手写请求封装、手写参数、手写断言，再不断根据接口变更维护用例。`ai-api-test` 的优势是：

- AI 可以直接参与用例编写和维护，减少重复编码。
- 抓包数据来自真实业务操作，比手工抄接口文档更贴近实际请求。
- 即使没有接口文档，也能通过抓包生成接口用例。
- 用例仍然是标准 Python + pytest 代码，不被平台能力限制。
- 生成后可以继续人工审查、调试、提交到代码仓库，适合团队长期维护。

### 对比网页版或打包应用式 AI 接口测试平台

很多 AI 接口测试平台把能力封装在网页或桌面应用中，使用方便，但往往会牺牲工程灵活性。`ai-api-test` 更适合需要落地到真实研发流程的团队：

- **更灵活**：代码、配置、运行方式、报告目录都在本地项目中，可自由修改。
- **更真实**：通过抓包覆盖真实页面操作产生的接口请求，不强依赖接口文档质量。
- **更可控**：测试代码保存在自己的仓库里，不需要把关键接口数据托管到外部平台。
- **更易集成**：天然适合接入 Git、CI、Allure、pytest marker、失败重跑等工程体系。
- **更适合二次开发**：可以扩展 `BaseAPI`、配置、fixture、skill 和用例模板。

## 快速使用

安装依赖：

```bash
pip install -r requirements.txt
```

配置被测系统地址：

```python
# config.py
base_url = "https://movie.douban.com"
```

运行用例：

```bash
python runpytest.py
```

执行指定目录：

```bash
python runpytest.py --case-path test_case/test_douban_case
```

生成并打开 Allure 报告：

```bash
python runpytest.py --case-path test_case/test_douban_case --open-report
```

报告生成位置：

```text
report/allure-report/<时间戳>/
```

使用 AI 新增或维护用例时，直接让 AI 读取并遵循：

```text
.claude/skills/api-test-common/SKILL.md
```

推荐给 AI 的任务格式：

```text
/api-test-common 

# 本次任务信息
- [接口方法文件] = test_case/page_api/xxx/xxx_api.py
- [接口方法位置] = 文件末尾
- [接口用例文件] = test_case/test_xxx_case/test_xxx_api.py
- [接口用例位置] = 文件末尾
- [fixture] = 选填：接口用例的前后置 fixture
- [用例名] = 自动生成

# 编写方式
请选择一种：
1. 抓包驱动：基于 runtime/latest.jsonl 生成
2. 参考已有用例：仿照指定文件或函数生成
3. cURL 手工：基于 cURL 请求和响应体生成
```

这个框架的目标不是替代工程师，而是让接口自动化从“人工重复写脚本”变成“AI 生成、工程师审查、项目持续沉淀”。
