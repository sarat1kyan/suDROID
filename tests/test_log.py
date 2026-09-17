import logging
from pathlib import Path

from sudroid.log import setup


def test_setup_creates_file_and_console(tmp_path: Path) -> None:
    f = tmp_path / "logs" / "s.log"
    console = setup("debug", json_mode=False, log_file=f)
    logging.getLogger("t").info("hello file")
    for h in logging.getLogger().handlers:
        h.flush()
    assert f.is_file()
    assert "hello file" in f.read_text()
    assert console.stderr is False


def test_json_mode_console_on_stderr(tmp_path: Path) -> None:
    console = setup("info", json_mode=True, log_file=tmp_path / "s.log")
    assert console.stderr is True
