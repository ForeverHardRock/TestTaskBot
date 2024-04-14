import datetime
import asyncio

from bot import bot
from functions import check_mailing, load_all_users


async def mailing() -> None:
    time_now = datetime.datetime.now().replace(microsecond=0)
    await asyncio.sleep(300)
    await send_mails(time_now)


async def send_mails(time_now):
    mails = await check_mailing(time_now)
    if mails:
        users_ids = await load_all_users()
        if users_ids:
            for mail in mails:
                for user_id in users_ids:
                    await bot.send_message(int(user_id[0]), mail[0])

