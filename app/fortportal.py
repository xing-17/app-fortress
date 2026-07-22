from __future__ import annotations

from app.common.setting.portal import PortalSetting

PORTAL_SETTING_PATH = "./setting/portal.yml"


def main():
    setting = PortalSetting.from_yaml(path=PORTAL_SETTING_PATH)
    # portal = FortPortalApi(setting=setting)
    print(setting.describe())
    # portal.run()


if __name__ == "__main__":
    main()
