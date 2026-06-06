# api-test-common

抓一次包，把接口自动化从“手写重复代码”变成“AI 生成可维护用例”。

`api-test-common` 是 `ai-api-test` 内置的通用接口自动化编写 Skill，适合复制到任意 Web 项目使用。它保留 pytest、接口方法层、测试用例层、Allure 报告和抓包生成流程，不绑定任何业务系统。

## 适合谁

- 想快速把页面操作沉淀成接口自动化用例的测试同学。
- 想按统一规范维护 pytest + Allure 接口测试项目的团队。
- 想让 AI 根据抓包、cURL、已有用例或 pytest 报错直接生成/修复用例的人。

## 能做什么

- 新增接口：抓包驱动、参考已有用例、cURL 手工三种方式。
- 维护接口：抓包驱动、参考已有用例、cURL 手工、pytest 报错驱动四种方式。
- 自动查重：按 `HTTP method + URL path` 检查接口方法是否已存在。
- 自动生成：接口方法、pytest 用例、Allure `epic/feature/story/step`。
- 自动验证：运行 pytest，输出 Allure 报告和修复建议。

AI 执行细则见 [`SKILL.md`](./SKILL.md)，流程图源码见 [`flow_chart/flow.md`](./flow_chart/flow.md)。

## 3 分钟试用

1. 配置目标站点：修改项目根 `config.py` 的 `base_url`，必须包含协议，例如 `https://example.com`。
2. 抓取接口：运行 `capture/start.bat`，浏览器代理设为 `127.0.0.1:12138`，完成页面操作。
3. 生成清单：运行 `python .claude/skills/api-test-common/tools/match_captures.py`，在 `runtime/capture_selection.md` 勾选要生成的接口。

随后把任务信息发给 AI，它会按规范生成接口方法和 pytest 用例。

## 新增任务模板

```text
# 本次任务信息
- [接口方法文件] = test_case/page_api/xxx/xxx_api.py
- [接口方法位置] = 文件末尾
- [接口用例文件] = test_case/test_xxx_case/test_xxx_api.py
- [接口用例位置] = 文件末尾
- [fixture] = 选填
- [用例名] = 完整中文功能名称
```

## 维护任务模板

```text
# 本次维护任务信息
- [接口用例文件] = test_case/test_xxx_case/test_xxx_api.py
- [接口用例位置] = test_xxx 或某测试类下的多个用例
```

## 抓包过滤

- `capture/allowed_prefixes.txt`：允许抓取的 URL 前缀，空文件表示不限制。
- `capture/blocked_prefixes.txt`：禁止抓取的 URL 前缀，空文件表示不限制。
- 过滤顺序：先执行 allowed，再执行 blocked。
- 静态资源和二进制响应始终过滤，避免无效数据污染接口清单。

## 常用命令

- 全量扫描已有接口方法，生成/刷新 URL 查重索引：
  ```bash
  python .claude/skills/api-test-common/tools/scan_page_api.py --full
  ```

- 读取 `runtime/latest.jsonl`，生成可勾选的抓包接口清单：
  ```bash
  python .claude/skills/api-test-common/tools/match_captures.py
  ```

- 运行指定目录下的接口用例，并生成 Allure 结果：
  ```bash
  python runpytest.py --case-path test_case/<target_case_dir>
  ```

## 关键约定

- Cookie、Authorization、token 不写死在接口方法或用例里。
- 接口方法只校验 HTTP `status_code`，业务断言写在 pytest 用例中。
- `runtime/latest.jsonl` 和 `runtime/capture_selection.md` 位于项目根 `runtime/`。
- Allure 字段由 AI 自动生成，也可根据用户说明或抓包语义调整。
