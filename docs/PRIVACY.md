[**English**](PRIVACY.md) | [简体中文](PRIVACY.zh-CN.md)

# Privacy

This tool is **purely local**: it listens on `127.0.0.1` only, and does not collect, upload, or write logs (by default). It contains no telemetry, statistics, or crash reporting.

## External network requests it may make

The following requests happen **only on explicit user action**, and each can be disabled:

| Feature | Target | Trigger | Can be disabled |
|---|---|---|---|
| Global top-sites list | `tranco-list.eu` | Clicking "test global Top 100" | Yes (no click = no request) |
| Public IP lookup | public IP API | Clicking "query public IP" | Yes (off by default) |
| External connectivity | user-configured target (default google.com / cloudflare.com) | health check or manual | Yes (target editable) |
| Site speed test | any user-entered domain | Clicking "speed test" | Yes |

## What it does NOT do

- Install persistent services or launch-at-login items
- Write logs to disk (by default; if enabled, MAC/IP/SSID are auto-masked)
- Collect or upload any network data, system info, or personal files
- Contain telemetry, statistics, or crash reporting

## Network identifiers in reports

Status and diagnostic reports show the machine's real DNS server addresses (e.g. `198.18.x.x`, carrier DNS) and interface / private IPs. These are rendered locally only — never uploaded, never written to disk.

> Planned: report export / sharing will mask sensitive values by default (DNS servers and private IPs like `198.18.x.x`, `192.168.x.x`, `10.x.x.x`), so internal network structure never leaks into issues or screenshots.
