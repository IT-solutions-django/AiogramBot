import asyncio
import re
import pytz
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import aiohttp
from settings import load_table
from typing import Optional, Dict, List, Union
from bs4 import BeautifulSoup
from datetime import datetime, time
import locale
import paramiko
from dotenv import dotenv_values
from settings import static
from keyboards.keyboard import buttons_command_server
from settings.logging_settings import logger

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


def is_day_active() -> Dict[str, set]:
    day_info_map = {
        'Будни': static.DayActiveMap.WEEKDAYS.value,
        'Кроме ВС': static.DayActiveMap.ALL_DAYS_EXCEPT_SUNDAY.value,
        'Все': static.DayActiveMap.FULL_WEEK.value,
    }

    return day_info_map


def split_message(text: str) -> List[str]:
    return [text[i:i + static.MessageLength.MAX_MESSAGE_LENGTH.value] for i in
            range(0, len(text), static.MessageLength.MAX_MESSAGE_LENGTH.value)]


async def show_options(obj: Union[types.CallbackQuery, types.Message], data_dict: Dict[str, dict], exclude_key: str,
                       action: Optional[str] = None) -> None:
    builder = InlineKeyboardBuilder()
    for key in data_dict.keys():
        if action is not None:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=f'{action}_{key}'))
        else:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=key))

    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())
        await obj.answer()
    elif isinstance(obj, types.Message):
        await obj.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())


async def get_balance(obj: Union[types.CallbackQuery, types.Message]) -> None:
    boobs = {data['Client']: {'Boobs': data['Boobs'], 'Company': field} for field, data in load_table.companies.items()
             if 'Boobs' in data}

    vladivostok_tz = pytz.timezone('Asia/Vladivostok')

    today_date = datetime.now(vladivostok_tz).strftime('%Y-%m-%d')
    today_date_json = datetime.now(vladivostok_tz).strftime('%-d %B')

    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(static.Message.LOAD_COMMAND.value)
    else:
        await obj.answer(static.Message.LOAD_COMMAND.value)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for client_name, boob_value in boobs.items():
            headers = {'Cookie': f"boobs={boob_value['Boobs']}"}
            balance_url = static.Urls.BALANCE_URL.value
            details_url = static.Urls.DETAILS_URL.get_url(date=today_date)

            tasks.append(
                fetch_data_balance(session, client_name, boob_value, balance_url, details_url, headers,
                                   today_date_json))

        results = await asyncio.gather(*tasks)

        messages = [result for result in results if result]

        if isinstance(obj, types.CallbackQuery):
            await obj.message.answer('\n'.join(messages), parse_mode='HTML')
            await obj.answer()
        else:
            await obj.answer('\n'.join(messages), parse_mode='HTML')


async def fetch_data_balance(session, client_name, boob_value, balance_url, details_url, headers, today_date_json):
    messages = []
    try:
        async with session.get(balance_url, headers=headers) as balance_response:
            if balance_response.status == 200:
                balance_data = await balance_response.json()
                balance = balance_data.get('canSpend')
                messages.append(f'<b>Клиент</b>: {client_name} ({boob_value["Company"]}), <b>Баланс</b>: {balance}.')
            else:
                messages.append(f'Ошибка получения баланса для {client_name}')

        async with session.get(details_url, headers=headers) as details_response:
            if details_response.status == 200:
                details_data = await details_response.json()
                transactions = details_data['data'].get('transactions', [])
                for day_data in transactions:
                    if day_data['date'] == today_date_json:
                        day_transactions = day_data['transactions']
                        replenishments = [trans for trans in day_transactions if
                                          'пополнение' in trans['description']['text'].lower()]
                        if replenishments:
                            messages.append(
                                f'<b>Пополнения</b> для {client_name}: {len(replenishments)} пополнение(ий) сегодня.\n')
                        else:
                            messages.append(f'Для {client_name} сегодня пополнений не было.\n')
                        break
                else:
                    messages.append(f'Для {client_name} сегодня пополнений не было.\n')
            else:
                messages.append(f'Ошибка при получении данных о пополнении для {client_name}')
    except Exception as e:
        messages.append(f'Ошибка для {client_name}: {str(e)}')

    return '\n'.join(messages)


async def get_server(obj: Union[types.CallbackQuery, types.Message]) -> None:
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_command_server)
    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(text=static.Message.CHOICE_COMMAND.value, reply_markup=keyboard)
        await obj.answer()
    else:
        await obj.answer(text=static.Message.CHOICE_COMMAND.value, reply_markup=keyboard)


async def fetch_advertisement_common(advertisement: Dict[str, str], all_dict: Dict[str, Dict[str, str]],
                                     vladivostok_time: time, current_day: int,
                                     check_problems: bool = False, company=None) -> str:
    id_advertisement: str = advertisement['_id']

    active_day_map: Dict[str, set] = is_day_active()
    active_day: Optional[set] = active_day_map.get(advertisement['weekday_active'], None)

    if active_day is None:
        logger.warning(
            f"Активный день для объявления '{id_advertisement}' не найден. Пожалуйста, добавьте его в active_day_map.")
        return f'Для объявления "{id_advertisement}" активный день не определён. Требуется обновление.\n\n'

    is_active_day: bool = current_day in active_day
    url: str = static.Urls.URL_ADVERTISEMENT.get_url(id_advertisement=id_advertisement)

    start_time = datetime.strptime(advertisement['start_time'].strip(), '%H.%M').time()
    end_time = datetime.strptime(advertisement['finish_time'].strip(), '%H.%M').time()

    if check_problems:
        if id_advertisement in all_dict and (not (start_time <= vladivostok_time <= end_time) or not is_active_day):
            return f'{company}. Для объявления "{url}" время вышло, но оно присутствует\n\n'
        elif not (id_advertisement in all_dict) and (start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'{company}. Для объявления "{url}" время не вышло, но его нет\n\n'
        else:
            return ''
    else:
        if id_advertisement in all_dict and (start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'{all_dict[id_advertisement]["name"]} - {all_dict[id_advertisement]["currencies"]}\n\n'
        elif id_advertisement in all_dict and (
                not (start_time <= vladivostok_time <= end_time) or not is_active_day):
            return f'Для объявления "{url}" время вышло, но оно присутствует\n\n'
        elif not (id_advertisement in all_dict) and (
                start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'Для объявления "{url}" время не вышло, но его нет\n\n'
        else:
            return f'Для объявления "{url}" вышло время\n\n'


async def load_advertisements_data(company_name: str, company_boobs: str) -> Dict[str, Dict[str, str]]:
    headers: Dict[str, str] = {'Cookie': f'boobs={company_boobs}'}
    base_url: str = static.Urls.URL_ACTUAL_BULLETINS.value
    page = 1
    all_dict = {}

    while True:
        url = f"{base_url}?page={page}"
        async with aiohttp.request('get', url, headers=headers, allow_redirects=False) as response:
            if response.status == 200:
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')

                currencies = soup.find_all('div', class_='bulletin-additionals__container')
                titles = soup.find_all('a', class_='bulletinLink bull-item__self-link auto-shy')

                if not currencies or not titles:
                    break

                page_data = {
                    re.search(r'(\d+)\.html', title['href']).group(1):
                        {
                            'currencies': div.text.strip(),
                            'name': title.text
                        }
                    for title, div in zip(titles, currencies)
                }
                all_dict.update(page_data)

                page += 1
            else:
                break
    return all_dict


async def handle_advertisements(callback: types.CallbackQuery, company_name: str, is_problem: bool):
    company_boobs = load_table.companies[company_name].get('Boobs', '')

    if not company_boobs:
        await callback.message.answer(static.Message.ERROR_COMMAND.value)
        await callback.answer()
        return

    await callback.message.answer(static.Message.LOAD_COMMAND.value)
    all_dict = await load_advertisements_data(company_name, company_boobs)

    company_advertisements = load_table.advertisements[company_name]
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    vladivostok_time = datetime.now(vladivostok_tz).time()
    current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

    tasks = [
        fetch_advertisement_common(advertisement, all_dict, vladivostok_time, current_day_vladivostok, is_problem)
        for advertisement in company_advertisements
        if advertisement['status'] == 'Подключено'
    ]

    message_lines = await asyncio.gather(*tasks)
    message = ''.join(message_lines)

    if not message:
        message = 'Для данной компании нет "проблемных" объявлений' if is_problem else 'Нет объявлений'

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


async def execute_ssh_command(command: str) -> tuple:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(static.SshData.IP.value, username=static.SshData.USERNAME.value,
                password=dotenv_values(".env")['PASSWORD_SSH'])

    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8')
    error = stderr.read().decode('utf-8')
    ssh.close()

    return output, error


async def get_service_logs() -> tuple:
    log_command = 'journalctl -u 100_cctv.service -n 5'
    return await execute_ssh_command(log_command)


async def fetch_data_for_advertisement(advertisements) -> str:
    company_boobs = load_table.companies[advertisements['client']].get('Boobs', '')
    if company_boobs:
        headers = {'Cookie': f'boobs={company_boobs}'}
        base_url = static.Urls.URL_ACTUAL_BULLETINS.value
        page = 1
        all_dict = {}

        while True:
            url = f"{base_url}?page={page}"
            async with aiohttp.request('get', url, headers=headers, allow_redirects=False) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')

                    currencies = soup.find_all('div', class_='bulletin-additionals__container')
                    titles = soup.find_all('a', class_='bulletinLink bull-item__self-link auto-shy')

                    if not currencies or not titles:
                        break

                    page_data = {
                        re.search(r'-(\d+)\.html', title['href']).group(1):
                            {
                                'currencies': div.text.strip(),
                                'name': title.text.strip()
                            }
                        for title, div in zip(titles, currencies)
                    }
                    all_dict.update(page_data)

                    page += 1
                else:
                    return f'Ошибка получения данных для {advertisements["client"]}\n\n'

        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        vladivostok_time = datetime.now(vladivostok_tz).time()
        current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

        task = await fetch_advertisement_common(
            advertisements, all_dict, vladivostok_time, current_day_vladivostok, False
        )

        return f'Компания "{advertisements["client"]}". ' + task
    else:
        return f'Для компании "{advertisements["client"]} - {advertisements["city"]}" действие недоступно\n\n'


async def problems_advertisements():
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    vladivostok_time = datetime.now(vladivostok_tz).time()
    current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

    advertisements = load_table.advertisements
    companies = load_table.companies

    task_all_dict = [
        load_advertisements_data(company, companies[company].get('Boobs', ''))
        for company in advertisements
        if companies[company].get('Boobs', '')
    ]

    all_dict = await asyncio.gather(*task_all_dict)
    merged_dict = {k: v for d in all_dict for k, v in d.items()}

    task_result = [
        fetch_advertisement_common(advertisement, merged_dict, vladivostok_time, current_day_vladivostok, True, company)
        for company, list_advertisements in advertisements.items()
        if companies[company].get('Boobs', '')
        for advertisement in list_advertisements
        if advertisement['status'] == 'Подключено'
    ]

    message_lines = await asyncio.gather(*task_result)
    message = ''.join(message_lines)

    return message
