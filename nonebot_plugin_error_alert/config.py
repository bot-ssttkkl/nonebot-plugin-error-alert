from nonebot import get_driver
from pydantic import BaseSettings


class Config(BaseSettings):
    error_alert_superuser_only: bool = True

    class Config:
        extra = "ignore"


conf = Config(**get_driver().config.dict())

__all__ = ("Config", "conf")
