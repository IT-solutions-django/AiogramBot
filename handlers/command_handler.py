from aiogram.filters import Command
from aiogram import types
from aiogram import Router

router = Router()


@router.message(Command("start"))
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
