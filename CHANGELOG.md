# 变更日志

本项目的重要变更记录在此文件中，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

## [0.1.1] - 2026-09-14

- 移除公开文档和帮助文本中的内部执行器、Handler 与账号示例。

## [0.1.0] - 2026-09-14

- 首次发布直接调用 XXL-Job Executor 的 Skill。
- 提供 `/beat` 探活、单次 `/run` 触发和当前 `/log` 回读；明确区分受理与业务结果。
- 支持环境变量 token、HTTPS/重定向保护、显式 jobId 与 Handler 规范化。
- 直调日志使用随机 63 位 `logId`，并提供 90% 语句覆盖率门禁。
- 添加本地模拟 Executor 的自动化测试。
