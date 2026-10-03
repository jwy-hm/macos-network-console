[**English**](CONTRIBUTING.md) | [简体中文](CONTRIBUTING.zh-CN.md)

# Contributing

Thanks for your interest! Issues and PRs are welcome.

## Development environment

```bash
make dev      # create venv + install ruff/pytest + editable install
make lint     # lint before committing
make test     # unit tests before committing
```

## Code style

- Python follows PEP 8 and PEP 484 (full type annotations), checked with `ruff`.
- Every module starts with `from __future__ import annotations`.
- External commands MUST go through `network_console.core.shell` — no direct `subprocess` + `shell=True`.

## Commit conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` refactor
- `chore:` miscellaneous

## Privacy requirements

Run `make privacy-check` before committing to ensure the code contains no personal identifiers (private IPs, personal directory paths, personal email domains, etc.).

## PR flow

1. Open an issue describing the problem or idea
2. Fork + create a branch
3. Run `make lint && make test && make privacy-check` before committing
4. Open a PR with a description of the changes
