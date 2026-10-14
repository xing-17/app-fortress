from __future__ import annotations

import pytest

from app.resource._global.identities import GlobalIdentities
from app.resource._global.logstreams import GlobalLogStreams
from app.resource._global.setting import GlobalSetting
from app.resource._global.sources import GlobalSources
from app.resource._global.stores import GlobalStores
from app.resource._global.vaults import GlobalVaults


@pytest.fixture(autouse=True)
def _reset_global_state():
    # All classes hold process-wide singleton state; isolate tests from each other.
    GlobalSetting.reset()
    GlobalIdentities.reset()
    GlobalStores.reset()
    GlobalVaults.reset()
    GlobalSources.reset()
    GlobalLogStreams.reset()
    yield
    GlobalSetting.reset()
    GlobalIdentities.reset()
    GlobalStores.reset()
    GlobalVaults.reset()
    GlobalSources.reset()
    GlobalLogStreams.reset()
