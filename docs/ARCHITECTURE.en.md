[简体中文](ARCHITECTURE.md) | [**English**](ARCHITECTURE.en.md)

# Architecture

## Overall structure

- **Backend**: Python standard-library `http.server` (no FastAPI/uvicorn), listens on `127.0.0.1` only.
- **Frontend**: single-page HTML + vanilla JS, no build step, no CDN; static assets served via a whitelist in `server.py`.
- **Platform layer**: `core/platform_macos.py` wraps macOS commands, all routed through `core.shell.run` (allowlist + timeout).
- **API layer**: `api/*.py` parses platform output into structured JSON; routes are centralized in `server.py`.

## Verification

Layered verification — all layers are required:

- **API layer**: `curl` + pytest. pytest includes unit tests (mocking `core.shell.run`)
  and raw-socket adversarial tests against a real server (`tests/test_security.py`).
- **Page layer**: must open a real browser or headless to confirm JS/CSS actually load
  and the page is interactive. `curl` only gets HTML source — it **cannot tell whether
  JS loaded**. P0 once missed a "static assets not routed, frontend blank" bug
  (commit `b848ae9`) for exactly this reason. Lesson: API all-green ≠ page works.
- **Smoke**: `make smoke` starts the server and checks the homepage + all static
  assets return 200.

## The five greens before each delivery

```
make lint && make test && make smoke && make privacy-check && make i18n-check
```

All five must pass before a PR can be opened.

## Known Limitations

Known limitations — intentional or deferred, not bugs:

- **`$USER` bare-word matching is fragile**: `privacy_check.py`'s dynamic `$USER`
  blacklist uses word-boundary matching, so it false-positives on generic identifiers
  in the code (e.g. `runner` on CI, variable names). Currently mitigated by the
  `_SKIP_USERS` skip set, which has no finite endpoint (each new environment word
  needs another entry). Future direction: match the username only in explicit
  contexts (e.g. `/Users/<name>/`, `<name>@host`) rather than scanning all text.
- **Diagnostic limits under TUN proxy**: all-`*` traceroute and fake-ip DNS results
  are normal proxy behavior; see README "Known behavior under proxy / VPN".
- **No automated page-render verification yet**: `make smoke` only checks static
  assets return 200, not JS rendering and interaction. Planned: introduce playwright
  as `make ui-smoke` to close the "rendering unverified" gap for good.
- **Wi-Fi channel / rate fields are not structured**: `channel` is a pre-built display
  string (`"36 (5GHz, 40MHz)"`), not split into `channel`/`band`/`width_mhz`; `rate_mbps`
  is the Tx rate without direction annotation. Deferred to P2 along with channel
  congestion visualization.
- **MAC / fake-ip masking is still frontend-only**: in privacy mode, MAC and fake-ip
  are masked by frontend functions; the data is still sent to the browser in plaintext.
  Only preferred networks is masked server-side. Will be unified backend-side in P2
  "report masking".
