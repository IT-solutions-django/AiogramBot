import asyncio
from aiogram import types
from aiogram import F, Router
from settings import load_table, static
from datetime import datetime, timedelta
import pytz
import re

from settings.logging_settings import logger
from settings.utils import split_message, show_options, get_balance, get_server, \
    handle_advertisements, execute_ssh_command, get_service_logs, fetch_data_for_advertisement, \
    problems_advertisements, fetch_advertisement_stats
from settings.static import Message
from main import bot
import aiogram.exceptions

router = Router()


@router.callback_query(F.data.startswith('get_company_'))
async def callback_get_company(callback: types.CallbackQuery) -> None:
    action = callback.data.split("_")[2]

    if action == 'info':
        await show_options(callback, load_table.companies, 'компанию', action)
    elif action == 'advertisements':
        await show_options(callback, load_table.companies, 'компанию', action)
    elif action == 'options':
        await show_options(callback, load_table.advertisements_options, 'options')
    elif action == 'price':
        await show_options(callback, load_table.companies, 'компанию', action)


@router.callback_query(lambda callback: callback.data in load_table.advertisements_options.keys())
async def callback_get_company_options(callback: types.CallbackQuery) -> None:
    options = callback.data
    company_info = load_table.advertisements_options[options]

    message_lines = [f'<b>Options "{options}"</b>\n\n']
    for idx, info in enumerate(company_info, 1):
        if info['status'] == 'Подключено':
            message_lines.append(f'ОБЪЯВЛЕНИЕ {idx}:')
            message_lines.extend([f'{field}: {data}' for field, data in info.items()])
            message_lines.append('\n')

    if len(message_lines) == 1:
        message_lines.append('Нет подключенных объявлений')

    message = '\n'.join(message_lines)

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


@router.callback_query(F.data == 'get_balance_users')
async def get_balance_callback(callback: types.CallbackQuery) -> None:
    await get_balance(callback)


@router.callback_query(F.data == 'get_command_server')
async def get_command_server(callback: types.CallbackQuery) -> None:
    await get_server(callback)


@router.callback_query(lambda callback: callback.data in ['start', 'stop', 'restart', 'status'])
async def command_server(callback: types.CallbackQuery) -> None:
    command = callback.data

    await callback.message.answer(Message.LOAD_COMMAND.value)

    service_command = f'systemctl {command} 100_cctv.service'
    output, error = await execute_ssh_command(service_command)

    if error:
        await callback.message.answer(f'{error.strip()}')
    else:
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        vladivostok_time = datetime.now(vladivostok_tz)
        await callback.message.answer(f'Команда "{command}" выполнена в {vladivostok_time}')

        if command == 'status':
            match = re.search(r'Active: (\w+ \(\w+\))', output)
            if match:
                status = match.group(1)
                await callback.message.answer(f'Статус службы: {status}')
            else:
                await callback.message.answer(f'Не удалось извлечь статус службы.')
        elif command in ['start', 'stop', 'restart']:
            log_output, log_error = await get_service_logs()
            if log_error:
                await callback.message.answer(f'Ошибка при чтении журнала: {log_error.strip()}')
            else:
                await callback.message.answer(f'Последние записи из журнала службы:\n\n{log_output.strip()}')

    await callback.answer()


@router.callback_query(F.data.startswith('options_price_'))
async def get_options_price(callback: types.CallbackQuery):
    options = callback.data.split("options_price_")[1]
    advertisements_options = load_table.advertisements_options[options]

    await callback.message.answer(Message.LOAD_COMMAND.value)

    tasks = [fetch_data_for_advertisement(advertisements) for advertisements in advertisements_options if
             advertisements['status'] == 'Подключено']
    results = await asyncio.gather(*tasks)

    message_lines = ''.join(results)

    if not message_lines:
        message_lines = f'<b>Options "{options}"</b>\n\nНет объявлений'
    else:
        message_lines = f'<b>Options "{options}"</b>\n\n' + message_lines

    parts = split_message(message_lines)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


@router.callback_query(lambda callback: callback.data.split('_')[1] in load_table.companies.keys())
async def callback_get_company_values(callback: types.CallbackQuery) -> None:
    action, company_name = callback.data.split("_")
    message = f'<b>Компания "{company_name}"</b>\n\n'

    if action == 'info':
        company_info = load_table.companies[company_name]
        for field, data in company_info.items():
            if field != 'Boobs':
                message += f'<b>{field}</b>: {data}\n'
        message += f'<b>Количество объявлений</b>: {len(load_table.advertisements[company_name])}\n'
        count_true_advertisements = len(list(filter(lambda advertisement: advertisement['status'] == 'Подключено',
                                                    load_table.advertisements[company_name])))
        message += f'<b>Количество подключенных объявлений</b>: {count_true_advertisements}'

    elif action == 'advertisements':
        company_info = load_table.advertisements[company_name]
        message_lines = [f'<b>Компания "{company_name}"</b>\n\n']
        for idx, info in enumerate(company_info, 1):
            if info['status'] == 'Подключено':
                message_lines.append(f'ОБЪЯВЛЕНИЕ {idx}:')
                message_lines.extend([f'{field}: {data}' for field, data in info.items()])
                message_lines.append('\n')

        if len(message_lines) == 1:
            message_lines.append('Нет подключенных объявлений')

        message = '\n'.join(message_lines)

    elif action == 'price':
        company_name = callback.data.split("price_")[1]
        await handle_advertisements(callback, company_name, is_problem=False)
        return

    elif action == 'statistics':
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')

        buttons_date = [
            [types.InlineKeyboardButton(text=str(datetime.now(vladivostok_tz).date() - timedelta(days=delta)),
                                        callback_data=f'{datetime.now(vladivostok_tz).date() - timedelta(days=delta)}_statistics_{company_name}')]
            for
            delta in range(0, 7)
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_date)

        await callback.message.answer(text='Выберите дату', reply_markup=keyboard)
        await callback.answer()
        return

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'get_options_for_price')
async def get_options_for_price(callback: types.CallbackQuery):
    await show_options(callback, load_table.advertisements_options, 'options', 'options_price')


@router.callback_query(F.data == 'get_problems_advertisements')
async def get_problems_advertisements(callback: types.CallbackQuery):
    await callback.message.answer(static.Message.LOAD_COMMAND.value)

    message = await problems_advertisements()

    if not message:
        message = 'Для компаний нет "проблемных" объявлений'

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


@router.callback_query(lambda callback: re.match(r'\d{4}-\d{2}-\d{2}_statistics_', callback.data))
async def get_statistics_for_date(callback: types.CallbackQuery):
    await callback.message.answer(static.Message.LOAD_COMMAND.value)

    company = callback.data.split('_')[2]
    date = callback.data.split('_')[0]
    advertisements = load_table.advertisements[company]
    boobs = load_table.companies[company].get('Boobs', '')

    tasks = [fetch_advertisement_stats(advertisement['_id'], boobs, date) for advertisement in advertisements if
             advertisement['status'] == 'Подключено']

    stat_company = await asyncio.gather(*tasks)

    lines = [f'{company} ({date}):\n']

    total_sums = {}

    for data_dict in stat_company:
        if isinstance(data_dict, dict):

            for id_advertisement, data in data_dict.items():
                lines.append(f'URL: https://www.farpost.ru/{id_advertisement}\n')
                for field, value in data.items():
                    lines.append(f'{field}: {value}\n')

                    if field not in total_sums:
                        total_sums[field] = 0
                    total_sums[field] += float(value)
        elif isinstance(data_dict, str):
            lines.append('Ошибка получения данных\n')
            break

        lines.append('\n')

    lines.append('Общие итоги:\n')
    for field, total in total_sums.items():
        lines.append(f'{field}: {total}\n')

    text = ''.join(lines)

    try:
        parts = split_message(text)
        for part in parts:
            await bot.send_message(chat_id=load_table.companies[company]['Chat_id'], text=part)
        await callback.message.answer(static.Message.STATISTICS_SUCCESS.value)
    except aiogram.exceptions.TelegramBadRequest:
        logger.error(f'Бот не может отправить "{company}" сообщение по данным статистики объявлений')
        await callback.message.answer(static.Message.STATISTICS_ERROR.value)

    await callback.answer()
