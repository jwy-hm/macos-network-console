from __future__ import annotations

import subprocess

from network_console.core.shell import Result, is_allowed, run


def test_is_allowed_read_only():
    assert is_allowed(["ifconfig"])
    assert is_allowed(["uname"])
    assert is_allowed(["ping", "-c", "1", "example.com"])


def test_is_allowed_rejects_deny_commands():
    for name in ["sudo", "sh", "bash", "zsh", "python", "python3", "perl", "open", "osascript"]:
        assert not is_allowed([name, "x"]), name


def test_is_allowed_rejects_unknown():
    assert not is_allowed(["cat", "/etc/hosts"])
    assert not is_allowed(["rm", "-rf", "/"])


def test_is_allowed_strips_path_prefix():
    assert not is_allowed(["/bin/sh", "-c", "echo hi"])


def test_run_allowed_command():
    result = run(["uname"])
    assert result.ok
    assert "Darwin" in result.value


def test_run_denied_command_returns_structured_error():
    result = run(["sudo", "ls"])
    assert not result.ok
    assert result.error == "命令被拒绝"


def test_run_timeout(monkeypatch):
    def _fake(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1)

    monkeypatch.setattr("subprocess.run", _fake)
    result = run(["curl", "http://example.com"], timeout=1)
    assert not result.ok
    assert "超时" in result.error


def test_run_timeout_preserves_partial_output(monkeypatch):
    def _fake(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=1, output=b"partial line\n")

    monkeypatch.setattr("subprocess.run", _fake)
    result = run(["traceroute", "8.8.8.8"], timeout=1)
    assert not result.ok
    assert "超时" in result.error
    # 部分输出应被保留并解码为 str（供解析器继续使用）
    assert isinstance(result.value, str)
    assert "partial line" in result.value


def test_run_nonzero_exit(monkeypatch):
    class _Done:
        returncode = 1
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr("subprocess.run", lambda *a, **k: _Done())
    result = run(["ping", "x"])
    assert not result.ok
    assert result.error == "exit code 1"
    assert result.hint == "boom"


def test_run_file_not_found(monkeypatch):
    def _fake(*args, **kwargs):
        raise FileNotFoundError("nope")

    monkeypatch.setattr("subprocess.run", _fake)
    result = run(["dig", "example.com"])
    assert not result.ok
    assert "不存在" in result.error


def test_result_to_dict():
    result = Result(ok=True, value="v", error="", hint="")
    assert result.to_dict() == {"ok": True, "value": "v", "error": "", "hint": ""}
