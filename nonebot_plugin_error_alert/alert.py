import traceback
from io import StringIO
from typing import Optional, NamedTuple, Type, Callable, Any

from nonebot import get_plugin_by_module_name
from nonebot import logger
from nonebot.internal.adapter import Event
from nonebot.log import default_format

from . import MODULE_NAME


class ErrorAlert(NamedTuple):
    summary: str
    exc_type: Optional[Type[BaseException]]

    @classmethod
    async def convert(cls, msg) -> "ErrorAlert":
        record = msg.record

        with StringIO() as sio:
            if record["message"]:
                sio.write(f"{record['message']}\n")

            sio.write("\n")

            sio.write(f"时间：{record['time'].strftime('%Y-%m-%d %H:%M:%S')}\n")
            sio.write(f"日志记录位置：File {record['file'].path}, line {record['line']}, in {record['function']}\n")

            if record["exception"] is not None:
                event: Optional[Event] = None
                plugins = []
                last_frame = None

                tb = record["exception"].traceback
                for frame, line_no in traceback.walk_tb(tb):
                    last_frame = frame
                    if "event" in frame.f_locals and isinstance(frame.f_locals["event"], Event):
                        event = frame.f_locals["event"]

                    plugin = get_plugin_by_module_name(frame.f_globals["__name__"])
                    if plugin is not None and (len(plugins) == 0 or plugin != plugins[-1]):
                        plugins.append(plugin)

                e = record["exception"].value
                sio.write(f"异常：<{type(e).__qualname__}> {e}\n")

                if last_frame is not None:
                    summary = traceback.extract_stack(last_frame)[-1]
                    sio.write(f"异常抛出位置：File {summary.filename}, line {summary.lineno}, in {summary.name}\n")
                    sio.write(f"    {summary.line}\n")

                if plugins is not None:
                    sio.write(f"插件：{'->'.join(map(lambda p: p.name, plugins))}\n")

                if event is not None:
                    sio.write(f"事件：{event.get_event_description()}\n")

            if record["thread"].name != 'MainThread':
                sio.write(f"线程：{record['thread'].name} (tid: {record['thread'].id})\n")

            if record["process"].name != 'MainProcess':
                sio.write(f"进程：{record['process'].name} (tid: {record['process'].id})\n")

            return ErrorAlert(summary=sio.getvalue().strip(),
                              exc_type=type(record["exception"].value) if record["exception"] is not None else None)


T_OBSERVER = Callable[[ErrorAlert], Any]

_observers = {}


def add_observer(key: str, observer):
    assert key not in _observers
    _observers[key] = observer


def remove_observer(key: str):
    if key not in _observers:
        raise LookupError()
    ob = _observers[key]
    del _observers[key]
    return ob


async def handler(msg):
    alert = await ErrorAlert.convert(msg)
    for ob in _observers.values():
        ob(alert)


logger.add(handler,
           level="ERROR",
           # 不处理本插件抛出的异常，避免无限套娃
           filter=lambda r: r["name"] != MODULE_NAME,
           format=default_format)
