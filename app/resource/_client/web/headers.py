from __future__ import annotations

_CHROME = "131"


class WebHeaders:
    _BASE: dict[str, str] = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{_CHROME}.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-AU,en;q=0.9",
        # brotli support requires the brotli library to be installed
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "sec-ch-ua": f'"Google Chrome";v="{_CHROME}", "Chromium";v="{_CHROME}", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
    }

    @classmethod
    def build(
        cls,
        updates: dict[str, str] | None = None,
    ) -> dict[str, str]:
        _base: dict[str, str] = cls._BASE.copy()
        if updates is not None:
            for _k, _v in updates.items():
                # force update for any provided header updates
                _base[_k] = _v
        return _base

    @classmethod
    def create(
        cls,
        values: dict[str, str] | None = None,
    ) -> dict[str, str]:
        _base: dict[str, str] = {}
        if values is not None:
            for _k, _v in values.items():
                _base[_k] = _v
        return _base
