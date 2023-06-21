nonebot-plugin-error-alert
========

当Bot发生运行错误时发送消息提醒

（插件基于截获logger的ERROR级别日志实现，其他插件在Matcher运行过程抛出异常，或是记录ERROR级别的日志，都将当作Bot运行错误处理）

## 卖家秀

![1](img/1.png)

## 指令

### `/error_alert subscribe`

订阅错误告警。发生错误时立即发送告警至本账号。

### `/error_alert subscribe <cron>`

订阅错误告警。但不会在发生错误时立即发送告警，而是在满足cron表达式的时间点统一发送该时间段发生的错误告警。

### `/error_alert unsubscribe`

取消订阅错误告警。

### `/error_alert show`

查看本账号订阅的错误告警。

## 配置项

### `error_alert_superuser_only`

是否仅允许超级用户调用指令。

默认值：`True`

## LICENSE

MIT License
