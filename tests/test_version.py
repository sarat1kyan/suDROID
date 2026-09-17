import re

import sudroid


def test_version_is_semver() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", sudroid.__version__)
