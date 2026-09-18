from __future__ import annotations

import pytest

from app.resource._global.identities import GlobalIdentities
from app.resource._global.setting import GlobalSetting


@pytest.fixture(autouse=True)
def _reset_global_state():
    # Both classes hold process-wide singleton state; isolate tests from each other.
    GlobalSetting.reset()
    GlobalIdentities.reset()
    yield
    GlobalSetting.reset()
    GlobalIdentities.reset()
