import asyncio

from aiogram import types
from aiogram import F, Router
import aiohttp

import paramiko

from settings import load_table

from bs4 import BeautifulSoup

from datetime import datetime
import pytz

import re

from dotenv import dotenv_values

from settings.utils import split_message, show_options, fetch_advertisement_data

if not load_table.companies or not load_table.advertisements_options or not load_table.advertisements:
    load_table.load_companies_from_sheet(load_table.service)

router = Router()


@router.callback_query(F.data.startswith('get_company_'))
async def callback_get_company(callback: types.CallbackQuery):
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
async def callback_get_company_options(callback: types.CallbackQuery):
    options = callback.data
    company_info = load_table.advertisements_options[options]

    message_lines = [f'<b>Options "{options}"</b>\n\n']
    for idx, info in enumerate(company_info, 1):
        message_lines.append(f'<b>ОБЪЯВЛЕНИЕ {idx}</b>:')
        message_lines.extend([f'<b>{field}</b>: {data}' for field, data in info.items()])
        message_lines.append('\n')
    message = '\n'.join(message_lines)

    await callback.message.answer(message, parse_mode='HTML')
    await callback.answer()


@router.callback_query(F.data == 'get_balance_users')
async def get_balance(callback: types.CallbackQuery):
    boobs = {data['Client']: {'Boobs': data['Boobs'], 'Company': field} for field, data in load_table.companies.items()
             if
             'Boobs' in data}

    await callback.message.answer('Идет загрузка баланса...')

    async with aiohttp.ClientSession() as session:
        messages = []
        for client_name, boob_value in boobs.items():
            headers = {'Cookie': f'boobs={boob_value['Boobs']}'}
            async with session.get(f'https://www.farpost.ru/personal/checkBalance/', headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    balance = data.get('canSpend')
                    messages.append(f'<b>Клиент</b>: {client_name} ({boob_value['Company']}), <b>Баланс</b>: {balance}')
                else:
                    messages.append(f'Ошибка получения баланса для {client_name}')
            session._cookie_jar._cookies.clear()
        await callback.message.answer('\n'.join(messages), parse_mode='HTML')
        await callback.answer()


@router.callback_query(F.data == 'get_command_server')
async def get_command_server(callback: types.CallbackQuery):
    buttons_command_server = [
        [types.InlineKeyboardButton(text='Start', callback_data='start')],
        [types.InlineKeyboardButton(text='Stop', callback_data='stop')],
        [types.InlineKeyboardButton(text='Restart', callback_data='restart')],
        [types.InlineKeyboardButton(text='Status', callback_data='status')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_command_server)
    await callback.message.answer(text='Выберите команду', reply_markup=keyboard)
    await callback.answer()


@router.callback_query(lambda callback: callback.data in ['start', 'stop', 'restart', 'status'])
async def command_server(callback: types.CallbackQuery):
    command = callback.data

    await callback.message.answer('Идет выполнение команды...')

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('217.18.62.157', username='root', password=dotenv_values(".env")['PASSWORD_SSH'])

    stdin, stdout, stderr = ssh.exec_command(f'systemctl {command} 100_cctv.service')
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')

    if command in ['start', 'stop', 'restart']:
        log_command = f'journalctl -u 100_cctv.service -n 5'
        stdin_log, stdout_log, stderr_log = ssh.exec_command(log_command)
        log_output = stdout_log.read().decode('utf-8')
        log_error = stderr_log.read().decode('utf-8')

    ssh.close()

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
            if log_error:
                await callback.message.answer(f'Ошибка при чтении журнала: {log_error.strip()}')
            else:
                await callback.message.answer(f'Последние записи из журнала службы:\n\n{log_output.strip()}')

    await callback.answer()


@router.callback_query(lambda callback: callback.data.split('_')[1] in load_table.companies.keys())
async def callback_get_company_values(callback: types.CallbackQuery):
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
        company_boobs = load_table.companies[company_name].get('Boobs', '')
        if company_boobs:
            await callback.message.answer('Загружаем данные...')

            headers = {'Cookie': f'boobs={company_boobs}'}
            url = 'https://www.farpost.ru/personal/actual/bulletins'
            async with aiohttp.request('get', url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()

                    soup = BeautifulSoup(content, 'html.parser')

                    currencies = soup.find_all('div', class_='service-card-head__link serviceStick applied')
                    titles = soup.find_all('a', class_='bulletinLink bull-item__self-link auto-shy')

                    all_dict = {title['href']: div.text.strip().split(',')[1]
                                for title, div in zip(titles, currencies)}

            company_advertisements = load_table.advertisements[company_name]

            vladivostok_tz = pytz.timezone('Asia/Vladivostok')
            vladivostok_time = datetime.now(vladivostok_tz).time()

            tasks = [fetch_advertisement_data(advertisement, all_dict, vladivostok_time)
                     for advertisement in company_advertisements]

            message_lines = await asyncio.gather(*tasks)
            message = ''.join(message_lines)
        else:
            message = 'Для данной компании действие недоступно'

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')
    await callback.answer()
