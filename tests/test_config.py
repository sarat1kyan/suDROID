from pathlib import Path

from sudroid.config import Config, load, write_default


def test_defaults(tmp_path: Path) -> None:
    cfg = load(tmp_path / "missing.toml", env={})
    assert cfg == Config()
    assert cfg.general.min_battery == 50
    assert cfg.tools.auto_download is True


def test_toml_override(tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text('[general]\nmin_battery = 30\n[magisk]\nchannel = "canary"\nkeep_verity = false\n')
    cfg = load(p, env={})
    assert cfg.general.min_battery == 30
    assert cfg.magisk.channel == "canary"
    assert cfg.magisk.keep_verity is False


def test_env_wins(tmp_path: Path) -> None:
    p = tmp_path / "c.toml"
    p.write_text("[general]\nmin_battery = 30\n")
    cfg = load(
        p,
        env={
            "SUDROID_GENERAL_MIN_BATTERY": "40",
            "SUDROID_TOOLS_ADB": "/x/adb",
            "SUDROID_TOOLS_AUTO_DOWNLOAD": "false",
        },
    )
    assert cfg.general.min_battery == 40
    assert cfg.tools.adb == "/x/adb"
    assert cfg.tools.auto_download is False


def test_unknown_keys_ignored(tmp_path: Path, caplog) -> None:  # type: ignore[no-untyped-def]
    p = tmp_path / "c.toml"
    p.write_text("[general]\nbogus = 1\n[other]\nx = 2\n")
    cfg = load(p, env={})
    assert cfg == Config()
    assert "bogus" in caplog.text
    assert "other" in caplog.text


def test_write_default_roundtrip(tmp_path: Path) -> None:
    p = write_default(tmp_path / "sub" / "config.toml")
    assert p.is_file()
    assert load(p, env={}) == Config()


def test_backup_dir_expands(tmp_path: Path) -> None:
    cfg = load(tmp_path / "x", env={"SUDROID_GENERAL_BACKUP_DIR": "~/b"})
    assert cfg.backup_dir == Path.home() / "b"
