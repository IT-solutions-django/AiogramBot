import asyncio
from aiogram import types
from aiogram import F, Router
from settings import load_table
from datetime import datetime
import pytz
import re
import logging
from settings.utils import split_message, show_options, get_balance, get_server, \
    handle_advertisements, execute_ssh_command, get_service_logs, fetch_data_for_advertisement

if not load_table.companies or not load_table.advertisements_options or not load_table.advertisements:
    logging.info('Началась загрузка данных')
    load_table.load_companies_from_sheet(load_table.service)
    logging.info('Загрузка данных завершилась')

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
        message_lines.append(f'ОБЪЯВЛЕНИЕ {idx}:')
        message_lines.extend([f'{field}: {data}' for field, data in info.items()])
        message_lines.append('\n')
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

    await callback.message.answer('Идет выполнение команды...')

    service_command = f'systemctl {command} 100_cctv.service'
    output, error = await execute_ssh_command(service_command)

    if error:
        await callback.message.answer(f'Ошибка при выполнении команды: {error.strip()}')
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

    await callback.message.answer('Загружаем данные...')

    tasks = [fetch_data_for_advertisement(advertisements) for advertisements in advertisements_options]
    results = await asyncio.gather(*tasks)

    message_lines = ''.join(results)
    message_lines = f'Options "{options}"\n\n' + message_lines

    parts = split_message(message_lines)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


@router.callback_query(F.data.startswith('problems_advertisements_'))
async def problems_advertisements(callback: types.CallbackQuery):
    company_name = callback.data.split("problems_advertisements_")[1]
    await handle_advertisements(callback, company_name, is_problem=True)


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
        message = '\n'.join(message_lines)

    elif action == 'price':
        company_name = callback.data.split("price_")[1]
        await handle_advertisements(callback, company_name, is_problem=False)
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
    await show_options(callback, load_table.companies, 'компанию', 'problems_advertisements')
