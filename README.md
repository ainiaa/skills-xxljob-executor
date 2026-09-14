# XXL-Job Executor

面向 Codex 的本地 Skill：直接调用 XXL-Job Executor 的 HTTP 接口触发已注册的 Handler，并回读该次执行日志。

当前发布版本：[0.1.0](VERSION)。未发布改动见 [变更日志](CHANGELOG.md) 的 Unreleased。

## 快速开始

在用户明确授权执行后，提供执行器地址、Handler 名称和 JSON 参数：

```bash
python3 scripts/run_xxl_job.py \
  --executor-url "http://10.93.1.143:9999" \
  --handler "syncAegisTradeFlowHandler" \
  --params '{"accountNos":["acct_x"],"startTime":1789344000000,"endTime":1789430400000}'
```

脚本依次请求 `/beat`、`/run` 与 `/log`：探活不成功时不会触发任务；触发后读取本次生成的 logId 的当前可用日志，不会自动重试。

### 带 access token 的 Executor

将 token 保存在用户环境或密钥管理工具中，仅把环境变量名传给脚本：

```bash
python3 scripts/run_xxl_job.py \
  --executor-url "https://executor.example.com" \
  --handler "exampleHandler" \
  --params '{"key":"value"}' \
  --access-token-env "XXL_JOB_ACCESS_TOKEN"
```

脚本会在 `/beat`、`/run`、`/log` 上统一携带 `XXL-JOB-ACCESS-TOKEN` Header；token 本身不会被打印。指定的环境变量不存在或为空时，脚本在发起网络请求前退出。

携带 token 时默认只允许 HTTPS 地址。仅限已确认安全的内网 HTTP Executor 时，显式增加 `--allow-insecure-http-token`；此开关会让 token 明文经过网络传输。

## 输入与结果

| 输入 | 要求 |
| --- | --- |
| `--executor-url` | Executor 的 HTTP/HTTPS 根地址，不含 query 或 fragment |
| `--handler` | 已部署的 `@XxlJob` Handler 名称 |
| `--params` | Handler 所需的 JSON 对象，字段和值保持用户原样输入 |
| `--job-id` | 可选；传真实 XXL-Job ID。缺省时根据 Handler 名生成稳定的正整数，避免所有直调任务共用 `0` |
| `--access-token-env` | 可选；保存 token 的环境变量名，不接收 token 明文 |
| `--allow-insecure-http-token` | 可选；仅与 `--access-token-env` 配合，用于受信任内网 HTTP 地址 |

`accepted` 只表示执行器已受理请求，不表示业务已完成或产生数据。`/log` 返回的当前日志通常只包含 XXL 包装层的启动、参数和 `ReturnT`；流水条数、下游响应和业务错误应继续在应用服务日志中核实。

## 使用 Skill

显式使用 `$xxl-job-executor`，并给出执行器地址、Handler 和参数。例如：

```text
使用 $xxl-job-executor 调用 http://10.93.1.143:9999/ 的 syncAegisTradeFlowHandler，参数为 {"accountNos":["acct_x"]}。
```

完整运行边界见 [SKILL.md](SKILL.md)。该 Skill 不用于修改 XXL-Job 管理台中的调度配置，也不会猜测凭据、改写参数或在失败后自行重试。

要用 `$xxl-job-executor` 自动发现此 Skill，需要将本目录安装或软链接到 Codex 已配置的 skills 根目录；否则仍可直接执行本 README 中的脚本命令。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

测试使用本地模拟 Executor，覆盖正常触发、XXL-Job 日志语义、稳定或显式 jobId、token Header 透传与 HTTPS/重定向保护、token 错误回显保护、token 缺失时停止，以及 `/beat` 失败时停止且不调用 `/run`。

覆盖率门禁为 90%（语句覆盖率）：

```bash
python3 -m coverage erase
python3 -m coverage run -m unittest discover -s tests -v
python3 -m coverage combine
python3 -m coverage report -m
```

## 许可

[MIT License](LICENSE)
