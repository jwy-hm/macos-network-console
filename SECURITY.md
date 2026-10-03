[**English**](SECURITY.md) | [简体中文](SECURITY.zh-CN.md)

# Security Policy

## Reporting a vulnerability

If you find a security vulnerability, please report it privately via **GitHub Security Advisory** — do **not** open a public issue.

- Submission: this repo's `Security` tab → `Report a vulnerability`
- We respond within **48 hours**

## Security design

This tool runs purely locally, listens on `127.0.0.1` only, and does not accept requests from outside the machine. Core security baseline:

- CSRF token validation (generated once at process start)
- Command allowlist + blocklist (rejects `sudo` / `sh` / `python` and other arbitrary-code shells)
- Security response headers (CSP / nosniff / no-referrer / X-Frame-Options)
- Request body size limit

See [docs/PRIVACY.md](docs/PRIVACY.md) and the source comments for details.
