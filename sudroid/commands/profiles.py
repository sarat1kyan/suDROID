from __future__ import annotations

import json

from sudroid.context import AppContext
from sudroid.device.profiles import all_profiles
from sudroid.ui.render import support_matrix


def run(ctx: AppContext) -> None:
    profiles = all_profiles()
    if ctx.json:
        data = [
            {
                "name": p.name,
                "vendor": p.vendor.value,
                "unlock_automatable": p.unlock_automatable,
                "flash_backend": p.flash_backend.value,
                "supports_test_boot": p.supports_test_boot,
                "unlock_url": p.unlock_url,
            }
            for p in profiles
        ]
        print(json.dumps(data, indent=2))
        return
    ctx.console.print(support_matrix(profiles))
