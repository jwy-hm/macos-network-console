[**English**](SECURITY-HYGIENE.md) | [简体中文](SECURITY-HYGIENE.zh-CN.md)

# Security Hygiene Checklist

This tool displays your **real network identifiers**. Before you screenshot, paste into an issue, paste into chat, or record a screen, run through this checklist.

## What counts as sensitive

| Type | Example | Why it's sensitive |
|---|---|---|
| SSID (Wi-Fi name) | home router name, hotspots with a person's name/address | can reverse-lookup address, name, even your home |
| BSSID | router MAC address | uniquely identifies one physical device, locatable |
| MAC address | NIC and other device MACs | uniquely identifies hardware, trackable across networks |
| Private IP | 192.168.x.x, 10.x.x.x, Tailscale 100.x | reveals your internal network structure and device count |
| Saved Wi-Fi list | every network you've joined | essentially your movement trail (hotels, places visited) |
| Device names | phone/computer hostnames, family device names | reveals real names, device models, family members |
| Public IP | your egress IP | can be located to city / ISP |
| Process / port | running services, listening ports | reveals installed software and open services |

## Before sharing

1. **Before screenshotting**: enable privacy mode, or manually mask SSID/BSSID/MAC/private IP.
2. **Before pasting CLI output**: `system_profiler`, `ifconfig`, `lsof`, `networksetup -listpreferredwirelessnetworks` output is almost entirely sensitive — check line by line.
3. **Before pasting git diff / commit**: if any of the above appears, replace with placeholders (`user`, `10.0.0.1`, `TestNetwork`).
4. **In commit messages too**: commit messages are public history. Writing a real IP/name there is a second leak. This project already had one such incident (see [INCIDENT-2026-10-04](INCIDENT-2026-10-04.md)).

## Self-check commands

```bash
# scan source + tests + docs (file contents)
make privacy-check

# also scan the full git history's commit messages
make privacy-check-history
```

Run both before committing; only push when both are green.

## Core principle

**"It's just for the AI / just for a friend / just temporary" is not an exception.** Chat logs may persist, may be used for training, may be accidentally forwarded. Once sensitive data leaves your machine, it cannot be taken back.

Tools (privacy-check) can catch files and git history, but not your screenshots and chat pastes. **Human habit is the weaker link.**
