from aiogram.filters import Command
from aiogram import types
from aiogram import Router
from settings.utils import show_options, get_balance, get_server, problems_advertisements, split_message
from settings import load_table, static
from settings.static import Message
from keyboards.keyboard import buttons_start

router = Router()


@router.message(Command("start"))
async def send_welcome(message: types.Message) -> None:
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_start)
    await message.answer(Message.CHOICE_COMMAND.value, reply_markup=keyboard)


@router.message(Command("info"))
async def command_get_company_info(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'info')


@router.message(Command("advertisements"))
async def command_get_company_advertisements(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'advertisements')


@router.message(Command("options"))
async def command_get_company_options(message: types.Message) -> None:
    await show_options(message, load_table.advertisements_options, 'options')


@router.message(Command("price"))
async def command_get_company_options(message: types.Message) -> None:
    await show_options(message, load_table.companies, 'компанию', 'price')


@router.message(Command("balance"))
async def get_balance_command(message: types.Message) -> None:
    await get_balance(message)


@router.message(Command("server"))
async def get_balance_command(message: types.Message) -> None:
    await get_server(message)


@router.message(Command("options_price"))
async def get_options_for_price_command(message: types.Message) -> None:
    await show_options(message, load_table.advertisements_options, 'options', 'options_price')


@router.message(Command("problems_advertisements"))
async def get_problems_advertisements_command(message: types.Message) -> None:
    await message.answer(static.Message.LOAD_COMMAND.value)

    text = await problems_advertisements()

    if not text:
        text = 'Для компаний нет "проблемных" объявлений'

    parts = split_message(text)
    for part in parts:
        await message.answer(text=part, parse_mode='HTML')


@router.message(Command('statistics_advertisements'))
async def statistics_advertisements_command(message):
    await show_options(message, load_table.companies, 'компанию', 'statistics')


@router.message(Command('table'))
async def send_url_table(message):
    await message.answer(f'Ссылка на таблицу (страница JSON)\n\n{static.Urls.URL_TABLE}')
