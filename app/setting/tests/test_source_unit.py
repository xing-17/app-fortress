from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from app.internal.constant.sourceprovider import SourceProvider
from app.setting import (
    ABSSourceSetting,
    FileStoreSetting,
    LocalVaultSetting,
    LogSetting,
    NSWVGSourceSetting,
    OSSStoreSetting,
    OSSVaultSetting,
    TushareSourceSetting,
    UnionSourceSetting,
)

_BASE = {"name": "s", "vault": "v", "store": "st"}


class TestUnionSourceSetting:
    def test_dispatches_on_provider(self):
        _adapter = TypeAdapter(UnionSourceSetting)
        assert isinstance(_adapter.validate_python({**_BASE, "provider": "abs"}), ABSSourceSetting)
        assert isinstance(_adapter.validate_python({**_BASE, "provider": "nsw_vg"}), NSWVGSourceSetting)
        assert isinstance(_adapter.validate_python({**_BASE, "provider": "tushare", "key": "k"}), TushareSourceSetting)

    def test_unknown_provider_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionSourceSetting).validate_python({**_BASE, "provider": "unknown"})

    def test_missing_provider_is_rejected(self):
        with pytest.raises(ValidationError):
            TypeAdapter(UnionSourceSetting).validate_python(_BASE)


class TestAbstractSourceBehavior:
    @pytest.mark.parametrize(
        ("cls", "provider"),
        [
            (ABSSourceSetting, SourceProvider.ABS),
            (NSWVGSourceSetting, SourceProvider.NSW_VG),
        ],
    )
    def test_provider_is_fixed(self, cls, provider):
        assert cls(**_BASE).provider == provider
        with pytest.raises(ValidationError):
            cls(**_BASE, provider="tushare")

    def test_defaults(self):
        _s = ABSSourceSetting(**_BASE)
        assert _s.description == ""
        assert _s.log is None

    def test_vault_accepts_name_or_nested_setting(self):
        assert ABSSourceSetting(**_BASE).vault == "v"
        _local = ABSSourceSetting(name="s", store="st", vault={"name": "v", "filesystem": "local", "path": "./v"})
        assert isinstance(_local.vault, LocalVaultSetting)
        _oss = ABSSourceSetting(
            name="s", store="st", vault={"name": "v", "filesystem": "oss", "bucket": "b", "region": "r"}
        )
        assert isinstance(_oss.vault, OSSVaultSetting)

    def test_store_accepts_name_or_nested_setting(self):
        assert ABSSourceSetting(**_BASE).store == "st"
        _file = ABSSourceSetting(name="s", vault="v", store={"name": "st", "storesystem": "file"})
        assert isinstance(_file.store, FileStoreSetting)
        _oss = ABSSourceSetting(
            name="s", vault="v", store={"name": "st", "storesystem": "oss", "bucket": "b", "region": "r"}
        )
        assert isinstance(_oss.store, OSSStoreSetting)

    def test_nested_vault_with_unknown_filesystem_is_rejected(self):
        with pytest.raises(ValidationError):
            ABSSourceSetting(name="s", store="st", vault={"name": "v", "filesystem": "unknown"})

    def test_log_accepts_nested_setting(self):
        _s = ABSSourceSetting(**_BASE, log={"name": "l"})
        assert isinstance(_s.log, LogSetting)
        assert _s.log.name == "l"

    def test_frn(self):
        assert ABSSourceSetting(**_BASE).frn == "setting:source:provider=abs:name=s"
        assert NSWVGSourceSetting(**_BASE).frn == "setting:source:provider=nsw_vg:name=s"

    def test_user_tags_cannot_override_reserved_tags(self):
        _s = ABSSourceSetting(**_BASE, tags={"name": "fake", "provider": "fake", "env": "prod"})
        assert _s.tags["name"] == "s"
        assert _s.tags["provider"] == "abs"
        assert _s.tags["env"] == "prod"


class TestTushareSourceSetting:
    def test_defaults(self):
        _s = TushareSourceSetting(**_BASE, key="k")
        assert _s.provider == SourceProvider.TUSHARE
        assert _s.session_ttl_hours == 0.5

    def test_requires_key(self):
        with pytest.raises(ValidationError):
            TushareSourceSetting(**_BASE)

    @pytest.mark.parametrize("value", [0, -1, -0.5])
    def test_session_ttl_hours_must_be_positive(self, value):
        with pytest.raises(ValidationError):
            TushareSourceSetting(**_BASE, key="k", session_ttl_hours=value)

    def test_session_ttl_hours_accepts_custom_value(self):
        assert TushareSourceSetting(**_BASE, key="k", session_ttl_hours=2).session_ttl_hours == 2

    def test_frn(self):
        assert TushareSourceSetting(**_BASE, key="k").frn == "setting:source:provider=tushare:name=s"
