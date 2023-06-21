from asyncio import Lock, create_task
from datetime import datetime
from enum import IntEnum
from io import StringIO
from typing import Optional

from apscheduler.triggers.cron import CronTrigger
from nonebot import Bot, get_bot, get_driver, logger
from nonebot.internal.adapter import Event
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_saa import extract_target, PlatformTarget, MessageFactory, Text, AggregatedMessageFactory
from pydantic import BaseModel, Field, validator

from .alert import ErrorAlert, add_observer, remove_observer

SUBSCRIBE = "subscribe"

plugin_data = get_plugin_data()
mutex = Lock()


class SubscribeType(IntEnum):
    immediate = 0
    cron = 1


class Subscribe(BaseModel):
    bot_id: str
    session: str
    target: PlatformTarget
    type: SubscribeType
    extra: dict = Field(default_factory=dict)

    @validator("target", pre=True, allow_reuse=True)
    def deserialize_target(cls, v):
        if isinstance(v, dict):
            return PlatformTarget.deserialize(v)
        else:
            return v

    @property
    def key(self) -> str:
        return f"subscribe_{self.bot_id}_{self.session}"


class ImmediateObserver:
    def __init__(self, subscribe: Subscribe):
        self.subscribe = subscribe

    def __call__(self, alert: ErrorAlert):
        async def _():
            try:
                await MessageFactory(Text(alert.summary)).send_to(self.subscribe.target,
                                                                  bot=get_bot(self.subscribe.bot_id))
            except BaseException as e:
                logger.exception(e)

        create_task(_())


class CronObserver:
    def __init__(self, subscribe: Subscribe):
        self.subscribe = subscribe
        self.pending = []
        self.last_sent = datetime.now()

    def start(self):
        trigger = parse_cron(self.subscribe.extra["cron"])
        scheduler.add_job(func=self.send, trigger=trigger, id=self.subscribe.key)

    def stop(self):
        try:
            scheduler.remove_job(self.subscribe.key)
        except LookupError:
            pass

    def __call__(self, alert: ErrorAlert):
        self.pending.append(alert)

    async def send(self):
        bot = get_bot(self.subscribe.bot_id)
        if bot is None:
            logger.warning(f"Bot {self.subscribe.bot_id} was not found")
            return

        pending = self.pending.copy()
        self.pending.clear()

        last_sent = self.last_sent
        self.last_sent = datetime.now()

        if len(pending) == 0:
            return

        with StringIO() as sio:
            sio.write(last_sent.strftime('%Y-%m-%d %H:%M'))
            sio.write("至今")

            sio.write(f"新增{len(pending)}次报错\n")

            grouped = {}
            for x in pending:
                if x.exc_type not in grouped:
                    grouped[x.exc_type] = []
                grouped[x.exc_type].append(x)

            groups = [(k, grouped[k]) for k in grouped]
            groups = sorted(groups,
                            key=lambda g: len(g[1]),
                            reverse=True)

            for i in range(0, min(len(groups), 10)):
                exc_type, li = groups[i]

                if exc_type is not None:
                    sio.write(f"<{exc_type.__qualname__}>")
                else:
                    sio.write("<非异常>")

                sio.write(f" {len(li)}次\n")

            if len(groups) > 10:
                sio.write("……")

        factories = list(map(lambda x: MessageFactory(Text(x.summary)), pending))

        if bot.type == "OneBot V11":
            for i in range(0, len(factories), 99):
                await AggregatedMessageFactory(
                    factories[i:min(len(factories), i + 50)]
                ).send_to(self.subscribe.target, bot=bot)
        else:
            for fac in factories:
                await fac.send_to(self.subscribe.target, bot=bot)


def parse_cron(cron: str) -> CronTrigger:
    segments = cron.split(" ")  # second minute hour day month day_of_week
    if len(segments) != 6:
        raise ValueError()

    if segments[3] == '?':
        segments[3] = '*'
    elif segments[5] == '?':
        segments[5] = '*'

    second, minute, hour, day, month, day_of_week = segments

    return CronTrigger(second=second, minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week)


@get_driver().on_startup
async def load_subscribe():
    async with mutex:
        subscribes = await plugin_data.config.get(SUBSCRIBE)
        if subscribes is None:
            return

        for sub in subscribes:
            subscribe = Subscribe.parse_obj(sub)
            if subscribe.type == SubscribeType.immediate:
                ob = ImmediateObserver(subscribe)
                add_observer(ob.subscribe.key, ob)
            elif subscribe.type == SubscribeType.cron:
                ob = CronObserver(subscribe)
                ob.start()
                add_observer(ob.subscribe.key, ob)


async def subscribe(bot: Bot, event: Event, cron: Optional[str]):
    if cron is not None:
        trigger = parse_cron(cron)
        subscribe = Subscribe(bot_id=bot.self_id,
                              session=event.get_session_id(),
                              target=extract_target(event),
                              type=SubscribeType.cron,
                              extra={"cron": cron})
        ob = CronObserver(subscribe)
    else:
        subscribe = Subscribe(bot_id=bot.self_id,
                              session=event.get_session_id(),
                              target=extract_target(event),
                              type=SubscribeType.immediate)
        ob = ImmediateObserver(subscribe)

    async with mutex:
        subscribes = await plugin_data.config.get(SUBSCRIBE)
        if subscribes is None:
            subscribes = []

        for i, sub in enumerate(subscribes):
            if sub["bot_id"] == subscribe.bot_id and sub["session"] == subscribe.session:
                old_ob = remove_observer(ob.subscribe.key)
                if isinstance(old_ob, CronObserver):
                    old_ob.stop()

                subscribes[i] = subscribe.dict()

                add_observer(ob.subscribe.key, ob)
                if isinstance(ob, CronObserver):
                    ob.start()

                break
        else:
            subscribes.append(subscribe.dict())
            add_observer(ob.subscribe.key, ob)
            if isinstance(ob, CronObserver):
                ob.start()

        await plugin_data.config.set(SUBSCRIBE, subscribes)


async def unsubscribe(bot: Bot, event: Event):
    async with mutex:
        subscribes = await plugin_data.config.get(SUBSCRIBE)
        if subscribes is None:
            return

        for i, sub in enumerate(subscribes):
            subscribe = Subscribe.parse_obj(sub)
            if subscribe.bot_id == bot.self_id and subscribe.session == event.get_session_id():
                subscribes.pop(i)

                old_ob = remove_observer(subscribe.key)
                if isinstance(old_ob, CronObserver):
                    old_ob.stop()

                break

        await plugin_data.config.set(SUBSCRIBE, subscribes)


async def get_subscribe(bot: Bot, event: Event) -> Optional[Subscribe]:
    async with mutex:
        subscribes = await plugin_data.config.get(SUBSCRIBE)
        if subscribes is None:
            return None

        for sub in subscribes:
            subscribe = Subscribe.parse_obj(sub)
            if subscribe.bot_id == bot.self_id and subscribe.session == event.get_session_id():
                return subscribe
