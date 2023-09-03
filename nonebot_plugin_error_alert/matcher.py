from io import StringIO

from nonebot import on_shell_command, Bot
from nonebot.exception import ParserExit
from nonebot.internal.adapter import Event
from nonebot.internal.matcher import Matcher
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser
from nonebot.typing import T_State

from .config import conf
from .subscribe import subscribe, unsubscribe, get_subscribe, SubscribeType

parser = ArgumentParser("error_alert")
subparsers = parser.add_subparsers(title="action", dest="action", required=True)

show_parser = subparsers.add_parser("show")

subscribe_parser = subparsers.add_parser("subscribe")
subscribe_parser.add_argument("--cron", dest="cron", required=False)

unsubscribe_parser = subparsers.add_parser("unsubscribe")


@on_shell_command(
    "error_alert",
    parser=parser,
    permission=SUPERUSER if conf.error_alert_superuser_only else None
).handle()
async def handle_cmd(state: T_State, matcher: Matcher, bot: Bot, event: Event):
    args = state["_args"]
    if isinstance(args, ParserExit):
        await matcher.send(args.message)
        return

    if args.action == "show":
        sub = await get_subscribe(bot, event)
        if sub is None:
            await matcher.send("当前未订阅")
        else:
            with StringIO() as sio:
                sio.write("类型: ")
                if sub.type == SubscribeType.immediate:
                    sio.write("立即推送")
                else:
                    sio.write("定时推送\n")
                    sio.write("cron：" + sub.extra["cron"])
                await matcher.send(sio.getvalue().strip())
    elif args.action == "subscribe":
        await subscribe(bot, event, args.cron)
        await matcher.send("ok")
    elif args.action == "unsubscribe":
        await unsubscribe(bot, event)
        await matcher.send("ok")
