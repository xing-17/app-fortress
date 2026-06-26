from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from typing import ClassVar

from dotenv import dotenv_values, load_dotenv


class CoreEnv:
    """
    应用环境变量管理。

    从 .env 文件加载环境变量并注入到 os.environ，支持敏感字段脱敏导出。
    默认从项目 env/.env 文件读取，文件不存在时静默跳过并触发缺失变量警告。

    Attributes:
        _SUPPORTED: 受支持（必须存在）的环境变量键名集合
        _SENSITIVE: 导出时需要脱敏的环境变量键名集合

    Examples:
        >>> env = CoreEnv.load()
        >>> env.check()
        >>> value = env.get("OSS_ACCESS_KEY_ID")
        >>> print(env.describe())

    """

    _SUPPORTED: ClassVar[set[str]] = {
        "OSS_ACCESS_KEY_ID",
        "OSS_ACCESS_KEY_SECRET",
    }
    _SENSITIVE: ClassVar[set[str]] = {
        "OSS_ACCESS_KEY_ID",
        "OSS_ACCESS_KEY_SECRET",
    }
    _default_root_dir: ClassVar[Path] = Path(__file__).parent.parent.parent.parent
    _default_env_path: ClassVar[Path] = _default_root_dir / "env" / ".env"

    def __init__(
        self,
        env_path: Path | str | None = None,
    ) -> None:
        self._env_path: Path = self._resolve_path(
            env_path,
            self._default_env_path,
        )
        self._env_values: list[str] = []

    @staticmethod
    def _resolve_path(
        path: str | Path | None = None,
        default: Path | None = None,
    ) -> Path:
        if path is None:
            return default
        return Path(path).expanduser().resolve()

    @classmethod
    def load(
        cls,
        env_path: Path | str | None = None,
        check: bool = True,
    ) -> "CoreEnv":
        instance = cls(env_path)
        instance._read_env()
        if check:
            instance.check()
        return instance

    def _read_env(self) -> None:
        if not self._env_path.is_file():
            self._env_values = []
            return

        # 记录本次从文件加载的 keys
        env_values = dotenv_values(self._env_path)
        self._env_values = list(env_values.keys())
        load_dotenv(
            dotenv_path=self._env_path,
            override=False,
        )

    def check(self) -> None:
        missing = []
        for key in self._SUPPORTED:
            if key not in self._env_values and key not in os.environ:
                missing.append(key)
        if missing:
            warning_msg = f"Missing required env vars: {missing}\n"
            warnings.warn(warning_msg, stacklevel=2)

    def inject(
        self,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        return {**os.environ, **(extra or {})}

    def get(
        self,
        key: str,
        default: str | None = None,
    ) -> str | None:
        return os.environ.get(key, default)

    def export(self) -> dict:
        result = {}
        for key in self._env_values:
            if key in self._env_values:
                source = "env"
            elif key in os.environ:
                source = "os"
            else:
                source = "missing"

            value = os.environ.get(key)
            if key in self._SENSITIVE:
                if value is not None:
                    value = value[:4] + "***"

            result[key] = {
                "value": value,
                "source": source,
            }

        return result

    def describe(self) -> dict:
        return json.dumps(
            self.export(),
            indent=4,
            ensure_ascii=False,
        )


# ── 全局单例 ──────────────────────────────────────────────────────────────────
# 模块加载时立即执行，确保在 CoreSetting / CoreLogGroup 之前完成 os.environ 注入
GlobalEnv: CoreEnv = CoreEnv.load()
