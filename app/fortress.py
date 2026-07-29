from __future__ import annotations

from app.common.setting.api import ApiSetting
from app.api.app import FortressApi


def main():
    API_SETTING_PATH = "./setting/api.yml"
    setting = ApiSetting.from_yaml(path=API_SETTING_PATH)
    api = FortressApi(setting=setting)
    api.run()


if __name__ == "__main__":
    main()
