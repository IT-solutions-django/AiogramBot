from aiogram.filters import Command
from aiogram import types
from aiogram import Router
from settings.utils import show_options, get_balance, get_server, problems_advertisements, split_message, position
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
    await message.answer(f'<b>Ссылка на таблицу (страница JSON)</b>\n\n{static.Urls.URL_TABLE.value}',
                         parse_mode='HTML')


@router.message(Command("position"))
async def handle_position(message):
    await message.answer("Обработка запущена, результаты будут отправлены позже.")

    company_result = {}

    result = await position()

    for idx, price in result.items():
        position_ad_table = int(load_table.info_for_id_ad[idx][0]["position"])
        if len(price) >= position_ad_table:
            cent = price[position_ad_table - 1]
            if cent % 5 != 0:
                if load_table.info_for_id_ad[idx][0]["client"] in company_result:
                    company_result[load_table.info_for_id_ad[idx][0]["client"]].update({idx: "На своей позиции"})
                else:
                    company_result[load_table.info_for_id_ad[idx][0]["client"]] = {idx: "На своей позиции"}
            else:
                if load_table.info_for_id_ad[idx][0]["client"] in company_result:
                    company_result[load_table.info_for_id_ad[idx][0]["client"]].update({idx: "Не на своей позиции"})
                else:
                    company_result[load_table.info_for_id_ad[idx][0]["client"]] = {idx: "Не на своей позиции"}
        else:
            if load_table.info_for_id_ad[idx][0]["client"] in company_result:
                company_result[load_table.info_for_id_ad[idx][0]["client"]].update({idx: "Не на своей позиции"})
            else:
                company_result[load_table.info_for_id_ad[idx][0]["client"]] = {idx: "Не на своей позиции"}

    result_message = "\n\n".join(
        f"{client}:\n{'\n'.join(f'{ad_id}: {status}' for ad_id, status in ads.items())}"
        for client, ads in company_result.items()
    )

    if not result_message:
        await message.answer("Нет данных о позициях.")
        return

    parts = split_message(result_message)
    for part in parts:
        await message.answer(text=part, parse_mode='HTML')
