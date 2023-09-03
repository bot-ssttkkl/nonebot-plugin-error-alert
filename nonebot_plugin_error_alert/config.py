from typing import Optional, List

from nonebot import get_driver
from pydantic import BaseSettings, root_validator


class Config(BaseSettings):
    error_alert_superuser_only: bool = True
    error_alert_plugins_blacklist: Optional[List[str]]
    error_alert_plugins_whitelist: Optional[List[str]]

    @root_validator(allow_reuse=True)
    def validate(cls, value):
        if value.get("error_alert_plugins_blacklist") is not None and value.get(
                "error_alert_plugins_whitelist") is not None:
            raise ValueError("不允许同时设置error_alert_plugins_blacklist与error_alert_plugins_whitelist")
        return value

    class Config:
        extra = "ignore"


conf = Config(**get_driver().config.dict())

__all__ = ("Config", "conf")
