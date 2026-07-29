from __future__ import annotations

from pydantic import Field

from app.bridges.resources.sources.base.setting import BaseSourceSetting


class TushareSourceSetting(BaseSourceSetting):
    """
    Tushare 数据源配置。

    继承 BaseSourceSetting 的所有字段，仅修改 setting_type 为 "tushare"
    以支持多态配置加载和类型识别。

    Attributes:
        setting_type (str): 固定为 "tushare"，用于类型标识
        include_fields (bool): 是否将 fields 列表拼接为逗号字符串传给 API，默认 False

    继承的所有字段：
        name (str): 数据源唯一标识
        domain(str): 数据源所属域名（如 "stock"）
        region (str): 数据源所属地区（如 "cn"）
        provider_type (str): Provider 类型（固定为 "tushare"）
        method (str): Tushare API 方法名（如 "daily", "moneyflow"）
        strategy (str): 数据流策略（如 "by_date", "by_tradedate"）
        partition (PartitionSetting): 分区配置
        paginate (PaginateSetting): 分页配置
        coolant (CoolantSetting): 速率限制配置
        retry (RetrySetting): 重试策略配置
        params (list[str]): 运行时参数名列表
        fields (list[str]): 请求字段列表（空列表表示全部字段）
        tags (dict): 数据源标签

    Example:
        >>> setting = TushareSourceSetting.from_yaml("items/tushare/tushare_stock_daily.yaml")
        >>> print(setting.setting_type)
        tushare
        >>> print(setting.method)
        daily

    """

    setting_type: str = "tushare"
    include_fields: bool = Field(
        default=False,
        description="是否将 fields 列表拼接为逗号字符串传给 API",
    )
