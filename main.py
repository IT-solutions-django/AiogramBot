from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio
from handlers import callback_handler

from dotenv import dotenv_values

API_TOKEN = dotenv_values(".env")['API_TOKEN']
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    buttons_start = [
        [types.InlineKeyboardButton(text='Показать информацию о компании', callback_data='get_company_info')],
        [types.InlineKeyboardButton(text='Показать объявления компании', callback_data='get_company_advertisements')],
        [types.InlineKeyboardButton(text='Показать объявления компании (по options)',
                                    callback_data='get_company_options')],
        [types.InlineKeyboardButton(text='Показать команды для удаленного сервера',
                                    callback_data='get_command_server')],
        [types.InlineKeyboardButton(text='Показать баланс пользователей', callback_data='get_balance_users')],
        [types.InlineKeyboardButton(text='Узнать цену объявлений компании', callback_data='get_company_price')]
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_start)
    await message.answer("Выберите действие:", reply_markup=keyboard)


async def main():
    dp.include_router(callback_handler.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
