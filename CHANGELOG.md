# Changelog

本项目的所有重要变更都会记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.1.0] - 2026-10-04

首个可用版本：纯本地 macOS 网络管理控制台。

### Added

- 系统状态总览：代理客户端、内网互联、外网连通性、路由冲突、DNS、内网设备、代理端口、默认路由（8 项并行检测）
- 网络接口：接口状态、IP、MAC、MTU、收发流量（内联 SVG 可视化）
- 连接监控：当前进程网络连接列表，进程名 / 端口过滤，权限边界标注
- 诊断工具箱：ping / traceroute / HTTP 头时间分解 / DNS 解析，能力探测 + 按工具超时 + 结果就地留存
- 设置：主题三态（跟随系统 / 浅色 / 深色）、隐私模式（隐藏 MAC / 公网 IP / fake-ip）
- 中英文双语（i18n），语言偏好记忆

### Security

- 仅监听 127.0.0.1，HTTP/1.1 + Content-Length
- CSRF token、命令白名单 + 黑名单、安全响应头（CSP / nosniff / no-referrer / X-Frame-Options）
- 请求体上限、Content-Type 校验、路径穿越防御
- 隐私自查脚本（私网 IP / fake-ip / 个人目录 / git 作者）+ i18n 检查，接入 CI

### Fixed

- lsof 列解析（NODE 列为协议而非地址）
- 诊断命令超时保留部分输出（traceroute 不再丢失已走完的跳）
- 代理客户端检测按 kind 过滤（Tailscale / aTrust 不再误判为代理）
