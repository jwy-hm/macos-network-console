from __future__ import annotations

from network_console.api import settings


def test_privacy_default_off(monkeypatch):
    monkeypatch.setattr(settings, "_privacy_enabled", False)
    assert settings.is_privacy_enabled() is False
    assert settings.get_privacy() == {"ok": True, "enabled": False}


def test_set_privacy_toggles(monkeypatch):
    monkeypatch.setattr(settings, "_privacy_enabled", False)
    r = settings.set_privacy(True)
    assert r == {"ok": True, "enabled": True}
    assert settings.is_privacy_enabled() is True
    r = settings.set_privacy(False)
    assert r == {"ok": True, "enabled": False}
    assert settings.is_privacy_enabled() is False


def test_set_privacy_coerces_bool(monkeypatch):
    monkeypatch.setattr(settings, "_privacy_enabled", False)
    # 非布尔输入应被强制转 bool
    assert settings.set_privacy(1)["enabled"] is True
    assert settings.set_privacy("")["enabled"] is False
