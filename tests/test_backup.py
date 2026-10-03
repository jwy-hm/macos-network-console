from __future__ import annotations

import os

from network_console import config
from network_console.core import backup


def test_backup_file_and_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path / "backups"))
    src = tmp_path / "local.json"
    src.write_text("{}")

    result = backup.backup_file(str(src))
    assert result.ok
    assert os.path.isfile(result.value)
    assert len(backup.list_backups()) == 1

    cleared = backup.clear()
    assert cleared.ok
    assert backup.list_backups() == []


def test_backup_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "BACKUP_DIR", str(tmp_path / "backups"))
    result = backup.backup_file(str(tmp_path / "nope.json"))
    assert not result.ok
    assert result.error
