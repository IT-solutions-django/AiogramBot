from aiogram import Bot, Dispatcher
import asyncio
from handlers import callback_handler, command_handler
from dotenv import dotenv_values
from settings import load_table
from settings.middleware import AccessMiddleware
from settings.schedulers import schedule_daily_statistics

API_TOKEN: str = dotenv_values(".env")['API_TOKEN']
bot: Bot = Bot(token=API_TOKEN)
dp: Dispatcher = Dispatcher()

allowed_chat_ids = [load_table.companies[company]['chat_id'] for company in load_table.companies]


async def main() -> None:
    dp.message.middleware(AccessMiddleware(allowed_chat_ids))
    dp.callback_query.middleware(AccessMiddleware(allowed_chat_ids))

    dp.include_router(command_handler.router)
    dp.include_router(callback_handler.router)

    schedule_daily_statistics(bot)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
