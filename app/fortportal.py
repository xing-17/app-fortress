from __future__ import annotations

from app.common.setting.portal import PortalSetting
from app.portal.app import FortPortalApi


def main():
    PORTAL_SETTING_PATH = "./setting/portal.yml"
    setting = PortalSetting.from_yaml(path=PORTAL_SETTING_PATH)
    portal = FortPortalApi(setting=setting)
    portal.run()


if __name__ == "__main__":
    main()
