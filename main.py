import asyncio
import logging
import sys

from handlers import router
from bot import bot, dp
from mailing import mailing


async def main() -> None:
    dp.include_routers(router)
    await asyncio.gather(
        dp.start_polling(bot),
        mailing()
    )


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, filename='bot.log')
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())

