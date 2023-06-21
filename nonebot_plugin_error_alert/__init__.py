from nonebot import require
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_saa")
require("nonebot_plugin_datastore")

MODULE_NAME = __name__.split(".")[-1]

from . import alert
from . import config
from . import matcher
from . import subscribe

import nonebot_plugin_saa

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="错误告警",
    description="当Bot发生运行错误时发送消息提醒",
    usage="""
/error_alert subscribe：订阅错误告警。发生错误时立即发送告警至本账号。
/error_alert subscribe <cron>：订阅错误告警。但不会在发生错误时立即发送告警，而是在满足cron表达式的时间点统一发送该时间段发生的错误告警。
/error_alert unsubscribe：取消订阅错误告警。
    """.strip(),
    homepage="https://github.com/bot-kuraku/nonebot-plugin-error-alert",
    config=Config,
    supported_adapters=nonebot_plugin_saa.__plugin_meta__.supported_adapters
)
