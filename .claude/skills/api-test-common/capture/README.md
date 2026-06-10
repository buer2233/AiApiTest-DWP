# capture - 抓包底座使用指引

本目录提供 mitmproxy 抓包脚本，默认端口 `12138`。

## 启动

```bat
start.bat
```

或：

```bash
mitmdump -s capture_addon.py --listen-port 12138
```

启动成功后会看到类似日志：

```text
[api-test-common] self.baseurl = https://www.gbif.org
[api-test-common] self.prefixes = []
[api-test-common] self.blocked_prefixes = []
[api-test-common] self.jsonl_path = ...\runtime\latest.jsonl
```

`self.baseurl = <empty>` 时，检查项目根 `config.py` 是否存在 `base_url = "https://..."`，且值必须包含协议和域名。

## 浏览器代理与证书

- HTTP/HTTPS 代理：`127.0.0.1:12138`
- HTTPS 抓包需要安装 mitmproxy 证书。
- 可访问 `http://mitm.it` 下载并安装证书。

## 落盘

抓包数据写入项目根：

```text
runtime/latest.jsonl
```

生成勾选草稿：

```bash
python ../tools/match_captures.py
```

输出：

```text
runtime/capture_selection.md
```

## 过滤规则

- 目标 host 来自项目根 `config.py` 的 `base_url`。
- `STATIC_SUFFIX` 静态资源后缀始终过滤。
- `BINARY_CT_PREFIXES` 二进制响应类型始终跳过响应体。
- `allowed_prefixes.txt` 为空时不按允许前缀过滤。
- `allowed_prefixes.txt` 有内容时，每行一个允许前缀，仅抓取匹配前缀的请求。
- `blocked_prefixes.txt` 为空时不按禁止前缀过滤。
- `blocked_prefixes.txt` 有内容时，每行一个禁止前缀，匹配前缀的请求不抓取。
- `allowed_prefixes.txt` 优先级更高：有允许前缀时先按允许前缀筛选，通过后再应用 `blocked_prefixes.txt` 排除。

登录、登出、埋点、心跳等接口不做内置路径判断；如需排除，请写入 `blocked_prefixes.txt`。

## JSONL 字段

| 字段 | 含义 |
|---|---|
| `ts` / `epoch` | 捕获时间 |
| `method` / `url` / `path` / `pure_path` | HTTP 请求信息 |
| `req_headers` | 请求头，Cookie/Authorization 已摘要 |
| `req_body` | 请求体文本 |
| `status` | HTTP 状态码 |
| `resp_content_type` | 响应 Content-Type |
| `resp_body` | 响应体，二进制已跳过 |
| `body_skipped` / `skip_reason` | 二进制或编码响应跳过标记 |

## 停止抓包

- mitmdump 窗口内按 `Ctrl+C`
- 双击 `stop.bat`
- 运行 `restart.bat` 可先停止再重启

## 清理建议

`runtime/latest.jsonl` 可能包含响应体业务数据。用例生成完成后，建议清理旧抓包文件。
