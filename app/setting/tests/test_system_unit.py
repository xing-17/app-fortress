from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.setting import (
    ABSSourceSetting,
    AliyunIdentitySetting,
    FileStoreSetting,
    LocalIdentitySetting,
    LocalVaultSetting,
    OSSStoreSetting,
    OSSVaultSetting,
    SystemLogSetting,
    SystemSetting,
)

_FULL = {
    "identities": [
        {"name": "a", "platform": "local"},
        {"name": "b", "platform": "aliyun", "type": "ak", "access_key_id": "id"},
    ],
    "stores": [
        {"name": "s", "storesystem": "file"},
        {"name": "o", "storesystem": "oss", "bucket": "b", "region": "r", "identity": "b"},
    ],
    "vaults": [
        {"name": "v", "filesystem": "local", "path": "./v"},
        {"name": "ov", "filesystem": "oss", "bucket": "b", "region": "r"},
    ],
    "sources": [{"name": "src", "provider": "abs", "vault": "v", "store": "s"}],
}


class TestSystemSetting:
    def test_defaults(self):
        _s = SystemSetting()
        assert _s.name == "fortress"
        assert _s.version == "0.0.1"
        assert _s.timezone is None
        assert isinstance(_s.log, SystemLogSetting)
        assert _s.log.name == "system"
        assert _s.identities == []
        assert _s.stores == []
        assert _s.vaults == []
        assert _s.sources == []

    def test_none_for_defaulted_field_falls_back_to_default(self):
        _s = SystemSetting.from_dict({"name": None, "identities": None})
        assert _s.name == "fortress"
        assert _s.identities == []

    def test_lists_are_not_shared_between_instances(self):
        _a, _b = SystemSetting(), SystemSetting()
        _a.stores.append(FileStoreSetting(name="s"))
        assert _b.stores == []

    def test_from_dict_builds_nested_union_settings(self):
        _s = SystemSetting.from_dict(_FULL)
        assert isinstance(_s.identities[0], LocalIdentitySetting)
        assert isinstance(_s.identities[1], AliyunIdentitySetting)
        assert isinstance(_s.stores[0], FileStoreSetting)
        assert isinstance(_s.stores[1], OSSStoreSetting)
        assert isinstance(_s.vaults[0], LocalVaultSetting)
        assert isinstance(_s.vaults[1], OSSVaultSetting)
        assert isinstance(_s.sources[0], ABSSourceSetting)

    def test_from_dict_rejects_invalid_nested_item(self):
        with pytest.raises(ValidationError):
            SystemSetting.from_dict({"stores": [{"name": "s", "storesystem": "unknown"}]})

    def test_from_dict_rejects_mismatched_identity_platform(self):
        with pytest.raises(ValidationError):
            SystemSetting.from_dict(
                {
                    "vaults": [
                        {
                            "name": "v",
                            "filesystem": "local",
                            "path": "./v",
                            "identity": {"name": "i", "platform": "aliyun"},
                        }
                    ]
                }
            )

    def test_from_yaml(self, tmp_path):
        _f = tmp_path / "system.yaml"
        _f.write_text("version: 1.2.3\nstores:\n  - name: s\n    storesystem: file\n", encoding="utf-8")
        _s = SystemSetting.from_yaml(_f)
        assert _s.version == "1.2.3"
        assert _s.stores[0].name == "s"

    def test_from_yaml_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SystemSetting.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_invalid_content(self, tmp_path):
        _f = tmp_path / "bad.yaml"
        _f.write_text("a: [unclosed\n", encoding="utf-8")
        with pytest.raises(ValueError, match="Failed to read YAML"):
            SystemSetting.from_yaml(_f)

    def test_export_round_trip(self):
        _s = SystemSetting.from_dict(_FULL)
        assert SystemSetting.from_dict(_s.export()).export() == _s.export()

    def test_describe_is_sorted_json(self):
        _text = SystemSetting().describe()
        assert _text.index('"alias"') < _text.index('"name"')
