from __future__ import annotations

from app.common.setting.system import SystemSetting
from app.interface.api import FortressApi

SETTING_PATH = "./setting/system.yml"


def main():
    setting = SystemSetting.from_yaml(
        path=SETTING_PATH,
    )
    api = FortressApi(
        setting=setting,
    )
    api.run()


if __name__ == "__main__":
    main()
