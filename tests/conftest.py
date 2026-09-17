from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


def getprop_text(name: str) -> str:
    return (FIXTURES / "getprop" / f"{name}.txt").read_text()
