from aiogram import Bot, Dispatcher
import asyncio
from handlers import callback_handler, command_handler
from dotenv import dotenv_values
from settings import load_table
from settings.middleware import AccessMiddleware
from settings.schedulers import schedule_daily_statistics, schedule_daily_data_loading, \
    schedule_problems_advertisements, schedule_daily_statistics_friday
import json

API_TOKEN: str = dotenv_values(".env")['API_TOKEN']
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()


async def main() -> None:
    with open('settings/admin.json') as file:
        chats_idx = json.load(file)['chat_id']

    if not load_table.companies or not load_table.advertisements_options or not load_table.advertisements:
        await load_table.load_companies_from_sheet(load_table.service)

    dp.message.middleware(AccessMiddleware(chats_idx))
    dp.callback_query.middleware(AccessMiddleware(chats_idx))

    dp.include_router(command_handler.router)
    dp.include_router(callback_handler.router)

    schedule_daily_statistics(bot)
    schedule_daily_data_loading()
    schedule_problems_advertisements(bot, chats_idx)
    schedule_daily_statistics_friday(bot)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
