from aiogram.filters import Command
from aiogram import types
from aiogram import Router
from settings.utils import show_options, get_balance, get_server
from settings import load_table
from settings.static import Message

router = Router()


@router.message(Command("start"))
async def send_welcome(message: types.Message) -> None:
    buttons_start = [
        [types.InlineKeyboardButton(text='Показать информацию о компании', callback_data='get_company_info')],
        [types.InlineKeyboardButton(text='Показать объявления компании', callback_data='get_company_advertisements')],
        [types.InlineKeyboardButton(text='Показать объявления компании (по options)',
                                    callback_data='get_company_options')],
        [types.InlineKeyboardButton(text='Показать команды для удаленного сервера',
                                    callback_data='get_command_server')],
        [types.InlineKeyboardButton(text='Показать баланс пользователей', callback_data='get_balance_users')],
        [types.InlineKeyboardButton(text='Узнать цену объявлений компании', callback_data='get_company_price')],
        [types.InlineKeyboardButton(text='Узнать цену объявлений компании (по options)',
                                    callback_data='get_options_for_price')],
        [types.InlineKeyboardButton(text='Объявления компании, требующие проверки',
                                    callback_data='get_problems_advertisements')]
    ]

    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_start)
    await message.answer(Message.CHOICE_COMMAND.value, reply_markup=keyboard)


@router.message(Command("get_company_info"))
async def command_get_company_info(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'info')


@router.message(Command("get_company_advertisements"))
async def command_get_company_advertisements(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'advertisements')


@router.message(Command("get_company_options"))
async def command_get_company_options(message: types.Message) -> None:
    await show_options(message, load_table.advertisements_options, 'options')


@router.message(Command("get_company_price"))
async def command_get_company_options(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'price')


@router.message(Command("get_balance_users"))
async def get_balance_command(message: types.Message) -> None:
    await get_balance(message)


@router.message(Command("get_command_server"))
async def get_balance_command(message: types.Message) -> None:
    await get_server(message)


@router.message(Command("get_options_for_price"))
async def get_options_for_price_command(message: types.Message) -> None:
    await show_options(message, load_table.advertisements_options, 'options', 'options_price')


@router.message(Command("get_problems_advertisements"))
async def get_problems_advertisements_command(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'problems_advertisements')
