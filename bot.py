#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import nonebot
from nonebot.adapters.qqguild import Adapter as QQGuildAdapter

nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(QQGuildAdapter)

nonebot.load_plugin("nonebot_plugin_escape_url")
nonebot.load_plugin("nonebot_plugin_error_alert")
nonebot.load_plugin("nonebot_plugin_test_error_alert")

if __name__ == "__main__":
    nonebot.run()
