from asyncio import create_task, sleep

from nonebot import on_command, logger


@on_command("raise").handle()
def _():
    raise RuntimeError("Oops")


@on_command("defer_raise").handle()
def _():
    async def do_raise():
        await sleep(1)
        raise RuntimeError("Oops")

    create_task(do_raise())


@on_command("error").handle()
def _():
    logger.error("Oops")
