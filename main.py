from aiogram import Bot, Dispatcher
import asyncio
from handlers import callback_handler, command_handler

from dotenv import dotenv_values

API_TOKEN = dotenv_values(".env")['API_TOKEN']
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


async def main():
    dp.include_router(command_handler.router)
    dp.include_router(callback_handler.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
