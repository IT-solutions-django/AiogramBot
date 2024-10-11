from aiogram import Bot, Dispatcher
import asyncio
from handlers import callback_handler, command_handler
from dotenv import dotenv_values
from settings import load_table
from settings.middleware import AccessMiddleware
from settings.schedulers import schedule_daily_statistics
import json

API_TOKEN: str = dotenv_values(".env")['API_TOKEN']
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()

allowed_chat_ids = [int(load_table.companies[company]['Chat_id']) for company in load_table.companies]

with open('settings/admin.json') as file:
    chats_idx = json.load(file)['chat_id']


async def main() -> None:
    dp.message.middleware(AccessMiddleware(chats_idx))
    dp.callback_query.middleware(AccessMiddleware(chats_idx))

    dp.include_router(command_handler.router)
    dp.include_router(callback_handler.router)

    schedule_daily_statistics(bot)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
