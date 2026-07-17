"""
综合测试：app.bridges.resources.secret.duckdb

覆盖范围
--------
- TestSecretDuckdbConfig        配置数据类基本属性
- TestSecretDuckdbInit          初始化和工厂方法
- TestToSQL                     SQL 生成（参数大写转换、scope 处理）
- TestCreate                    创建 secret 操作
- TestCheck                     检查 secret 是否存在
- TestDrop                      删除 secret 操作
- TestListAll                   列出所有 secret
- TestExport                    export() 方法
- TestDescribe                  describe() 方法
"""

from __future__ import annotations

import json

import duckdb
import pytest

from app.bridges.resources.secret.duckdb import SecretDuckdb, SecretDuckdbConfig

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def duckdb_conn():
    """创建临时 DuckDB 内存连接"""
    conn = duckdb.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def sample_config():
    """创建示例配置"""
    return SecretDuckdbConfig(
        type="s3",
        name="test_secret",
        params={
            "key_id": "test_key",
            "secret": "test_secret_value",
            "region": "cn-shanghai",
            "endpoint": "oss.aliyuncs.com",
        },
        scope="s3://test-bucket",
    )


@pytest.fixture
def sample_secret(sample_config):
    """创建示例 SecretDuckdb 实例"""
    return SecretDuckdb(sample_config)


# ──────────────────────────────────────────────────────────────────────────────
# TestSecretDuckdbConfig
# ──────────────────────────────────────────────────────────────────────────────


class TestSecretDuckdbConfig:
    """测试 SecretDuckdbConfig 数据类基本属性"""

    def test_config_has_type(self, sample_config):
        """测试配置包含 type 属性"""
        assert hasattr(sample_config, "type")
        assert sample_config.type == "s3"

    def test_config_has_name(self, sample_config):
        """测试配置包含 name 属性"""
        assert hasattr(sample_config, "name")
        assert sample_config.name == "test_secret"

    def test_config_has_params(self, sample_config):
        """测试配置包含 params 属性"""
        assert hasattr(sample_config, "params")
        assert isinstance(sample_config.params, dict)
        assert "key_id" in sample_config.params

    def test_config_has_scope(self, sample_config):
        """测试配置包含 scope 属性"""
        assert hasattr(sample_config, "scope")
        assert sample_config.scope == "s3://test-bucket"

    def test_config_scope_can_be_none(self):
        """测试配置的 scope 可以为 None"""
        config = SecretDuckdbConfig(
            type="s3",
            name="test",
            params={},
        )
        assert config.scope is None


# ──────────────────────────────────────────────────────────────────────────────
# TestSecretDuckdbInit
# ──────────────────────────────────────────────────────────────────────────────


class TestSecretDuckdbInit:
    """测试 SecretDuckdb 初始化和工厂方法"""

    def test_init_with_config(self, sample_config):
        """测试使用配置初始化"""
        secret = SecretDuckdb(sample_config)
        assert secret.config == sample_config
        assert secret.name == sample_config.name

    def test_from_params_creates_instance(self):
        """测试 from_params 工厂方法创建实例"""
        secret = SecretDuckdb.from_params(
            type="s3",
            name="factory_secret",
            params={"key_id": "xxx"},
            scope="s3://bucket",
        )
        assert isinstance(secret, SecretDuckdb)
        assert secret.name == "factory_secret"
        assert secret.config.type == "s3"

    def test_from_params_without_scope(self):
        """测试 from_params 不带 scope 参数"""
        secret = SecretDuckdb.from_params(
            type="s3",
            name="no_scope_secret",
            params={"key_id": "xxx"},
        )
        assert secret.config.scope is None


# ──────────────────────────────────────────────────────────────────────────────
# TestToSQL
# ──────────────────────────────────────────────────────────────────────────────


class TestToSQL:
    """测试 to_sql() 方法"""

    def test_to_sql_returns_string(self, sample_secret):
        """测试 to_sql 返回字符串"""
        sql = sample_secret.to_sql()
        assert isinstance(sql, str)

    def test_to_sql_contains_create_statement(self, sample_secret):
        """测试 SQL 包含 CREATE OR REPLACE SECRET 语句"""
        sql = sample_secret.to_sql()
        assert "CREATE OR REPLACE SECRET" in sql
        assert "test_secret" in sql

    def test_to_sql_contains_type(self, sample_secret):
        """测试 SQL 包含 TYPE"""
        sql = sample_secret.to_sql()
        assert "TYPE s3" in sql

    def test_to_sql_contains_provider(self, sample_secret):
        """测试 SQL 包含 PROVIDER config"""
        sql = sample_secret.to_sql()
        assert "PROVIDER config" in sql

    def test_to_sql_params_are_uppercase(self, sample_secret):
        """测试参数名会转换为大写"""
        sql = sample_secret.to_sql()
        assert "KEY_ID" in sql
        assert "SECRET" in sql
        assert "REGION" in sql
        assert "ENDPOINT" in sql
        # 确保不包含小写
        assert "key_id" not in sql
        assert "secret 'test" not in sql.lower().replace("secret", "SECRET")

    def test_to_sql_contains_param_values(self, sample_secret):
        """测试 SQL 包含参数值"""
        sql = sample_secret.to_sql()
        assert "'test_key'" in sql
        assert "'test_secret_value'" in sql
        assert "'cn-shanghai'" in sql
        assert "'oss.aliyuncs.com'" in sql

    def test_to_sql_contains_scope_when_provided(self, sample_secret):
        """测试当提供 scope 时 SQL 包含 SCOPE"""
        sql = sample_secret.to_sql()
        assert "SCOPE" in sql
        assert "'s3://test-bucket'" in sql

    def test_to_sql_no_scope_when_none(self):
        """测试当 scope 为 None 时 SQL 不包含 SCOPE"""
        config = SecretDuckdbConfig(
            type="s3",
            name="no_scope",
            params={"key_id": "xxx"},
            scope=None,
        )
        secret = SecretDuckdb(config)
        sql = secret.to_sql()
        assert "SCOPE" not in sql


# ──────────────────────────────────────────────────────────────────────────────
# TestCreate
# ──────────────────────────────────────────────────────────────────────────────


class TestCreate:
    """测试 create() 方法"""

    def test_create_executes_without_error(self, sample_secret, duckdb_conn):
        """测试 create 方法执行无错误"""
        sample_secret.create(duckdb_conn)
        # 如果没有异常抛出，测试通过

    def test_create_makes_secret_exist(self, sample_secret, duckdb_conn):
        """测试 create 后 secret 存在"""
        sample_secret.create(duckdb_conn)
        result = duckdb_conn.execute(
            "SELECT name FROM duckdb_secrets() WHERE name = ?",
            [sample_secret.name],
        ).fetchall()
        assert len(result) == 1
        assert result[0][0] == sample_secret.name

    def test_create_can_replace_existing_secret(self, sample_secret, duckdb_conn):
        """测试 create 可以替换已存在的 secret"""
        sample_secret.create(duckdb_conn)
        sample_secret.create(duckdb_conn)  # 再次创建不应报错
        result = duckdb_conn.execute(
            "SELECT COUNT(*) FROM duckdb_secrets() WHERE name = ?",
            [sample_secret.name],
        ).fetchone()
        assert result[0] == 1  # 只有一个 secret


# ──────────────────────────────────────────────────────────────────────────────
# TestCheck
# ──────────────────────────────────────────────────────────────────────────────


class TestCheck:
    """测试 check() 方法"""

    def test_check_returns_false_when_not_exists(self, sample_secret, duckdb_conn):
        """测试当 secret 不存在时返回 False"""
        result = sample_secret.check(duckdb_conn)
        assert result is False

    def test_check_returns_true_when_exists(self, sample_secret, duckdb_conn):
        """测试当 secret 存在时返回 True"""
        sample_secret.create(duckdb_conn)
        result = sample_secret.check(duckdb_conn)
        assert result is True

    def test_check_returns_false_after_drop(self, sample_secret, duckdb_conn):
        """测试删除后 check 返回 False"""
        sample_secret.create(duckdb_conn)
        sample_secret.drop(duckdb_conn)
        result = sample_secret.check(duckdb_conn)
        assert result is False


# ──────────────────────────────────────────────────────────────────────────────
# TestDrop
# ──────────────────────────────────────────────────────────────────────────────


class TestDrop:
    """测试 drop() 方法"""

    def test_drop_executes_without_error(self, sample_secret, duckdb_conn):
        """测试 drop 方法执行无错误"""
        sample_secret.drop(duckdb_conn)
        # 如果没有异常抛出，测试通过

    def test_drop_removes_existing_secret(self, sample_secret, duckdb_conn):
        """测试 drop 删除已存在的 secret"""
        sample_secret.create(duckdb_conn)
        sample_secret.drop(duckdb_conn)
        result = duckdb_conn.execute(
            "SELECT name FROM duckdb_secrets() WHERE name = ?",
            [sample_secret.name],
        ).fetchall()
        assert len(result) == 0

    def test_drop_nonexistent_secret_no_error(self, sample_secret, duckdb_conn):
        """测试删除不存在的 secret 不会报错"""
        sample_secret.drop(duckdb_conn)  # 不应抛出异常


# ──────────────────────────────────────────────────────────────────────────────
# TestListAll
# ──────────────────────────────────────────────────────────────────────────────


class TestListAll:
    """测试 list_all() 静态方法"""

    def test_list_all_returns_list(self, duckdb_conn):
        """测试 list_all 返回列表"""
        result = SecretDuckdb.list_all(duckdb_conn)
        assert isinstance(result, list)

    def test_list_all_empty_when_no_secrets(self, duckdb_conn):
        """测试没有 secret 时返回空列表"""
        result = SecretDuckdb.list_all(duckdb_conn)
        assert len(result) == 0

    def test_list_all_contains_created_secrets(self, sample_secret, duckdb_conn):
        """测试 list_all 包含已创建的 secret"""
        sample_secret.create(duckdb_conn)
        result = SecretDuckdb.list_all(duckdb_conn)
        assert sample_secret.name in result

    def test_list_all_contains_multiple_secrets(self, duckdb_conn):
        """测试 list_all 返回多个 secret"""
        secret1 = SecretDuckdb.from_params(type="s3", name="secret1", params={"key_id": "xxx"})
        secret2 = SecretDuckdb.from_params(type="s3", name="secret2", params={"key_id": "yyy"})
        secret1.create(duckdb_conn)
        secret2.create(duckdb_conn)
        result = SecretDuckdb.list_all(duckdb_conn)
        assert len(result) == 2
        assert "secret1" in result
        assert "secret2" in result


# ──────────────────────────────────────────────────────────────────────────────
# TestExport
# ──────────────────────────────────────────────────────────────────────────────


class TestExport:
    """测试 export() 方法"""

    def test_export_returns_dict(self, sample_secret):
        """测试 export 返回字典"""
        result = sample_secret.export()
        assert isinstance(result, dict)

    def test_export_contains_type(self, sample_secret):
        """测试 export 包含 type"""
        result = sample_secret.export()
        assert "type" in result
        assert result["type"] == "s3"

    def test_export_contains_name(self, sample_secret):
        """测试 export 包含 name"""
        result = sample_secret.export()
        assert "name" in result
        assert result["name"] == "test_secret"

    def test_export_contains_scope(self, sample_secret):
        """测试 export 包含 scope"""
        result = sample_secret.export()
        assert "scope" in result
        assert result["scope"] == "s3://test-bucket"

    def test_export_scope_can_be_none(self):
        """测试 export 的 scope 可以为 None"""
        config = SecretDuckdbConfig(
            type="s3",
            name="test",
            params={},
        )
        secret = SecretDuckdb(config)
        result = secret.export()
        assert result["scope"] is None


# ──────────────────────────────────────────────────────────────────────────────
# TestDescribe
# ──────────────────────────────────────────────────────────────────────────────


class TestDescribe:
    """测试 describe() 方法"""

    def test_describe_returns_string(self, sample_secret):
        """测试 describe 返回字符串"""
        result = sample_secret.describe()
        assert isinstance(result, str)

    def test_describe_returns_valid_json(self, sample_secret):
        """测试 describe 返回有效的 JSON"""
        result = sample_secret.describe()
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_describe_contains_all_fields(self, sample_secret):
        """测试 describe 包含所有字段"""
        result = sample_secret.describe()
        parsed = json.loads(result)
        assert "type" in parsed
        assert "name" in parsed
        assert "scope" in parsed
