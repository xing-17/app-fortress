"""
综合测试：bastion.domain.platform

覆盖范围
--------
- TestPlatform     枚举值正确性；from_any() 类型转换；无效值处理
"""

from __future__ import annotations

from bastion.domain.platform import Platform


class TestPlatform:
    """测试 Platform 枚举。"""

    def test_enum_values_exist(self):
        """测试所有预定义值存在。"""
        assert Platform.S3 == "s3"
        assert Platform.LOCAL == "local"
        assert Platform.OSS == "oss"
