import asyncio
import re
import random
from fake_useragent import UserAgent
import aiogram.exceptions
import pytz
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import aiohttp
from paramiko.ssh_exception import AuthenticationException, SSHException
from settings import load_table
from typing import Optional, Dict, List, Union
from bs4 import BeautifulSoup
from datetime import datetime, time, timedelta
import locale
import paramiko
from dotenv import dotenv_values
from settings import static
from keyboards.keyboard import buttons_command_server
from settings.logging_settings import logger
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

proxies = [
    "3nbFwoBiE8TZ:RNW78Fm5@pool.proxy.market:10384",
    "3nbFwoBiE8TZ:RNW78Fm5@pool.proxy.market:10385",
    "3nbFwoBiE8TZ:RNW78Fm5@pool.proxy.market:10386",
    "3nbFwoBiE8TZ:RNW78Fm5@pool.proxy.market:10387",
    "3nbFwoBiE8TZ:RNW78Fm5@pool.proxy.market:10388",
]


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


def check_position(position_ad):
    company_result = {}

    for idx, price in position_ad.items():
        position_ad_table = int(load_table.info_for_id_ad[idx][0]["position"])
        if len(price) >= position_ad_table:
            cent = price[position_ad_table - 1]
            if cent % 5 != 0:
                company_result[idx] = 'На своей позиции'
            else:
                company_result[idx] = 'Не на своей позиции'
        else:
            company_result[idx] = 'Не на своей позиции'

    return company_result


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
        async with session.get(balance_url, headers=headers, allow_redirects=False) as balance_response:
            if balance_response.status == 200:
                balance_data = await balance_response.json()
                balance = balance_data.get('canSpend')
                messages.append(
                    f'<b>Клиент: {client_name.strip()} ({boob_value["Company"].strip()})</b>\nБаланс: {balance}')
            else:
                messages.append(f'Ошибка получения баланса для {client_name}\n')

        page = 1
        len_replenishments = 0
        flag_page = True
        while True:
            url = f'{details_url}&page={page}'
            async with session.get(url, headers=headers, allow_redirects=False) as details_response:
                if details_response.status == 200:
                    details_data = await details_response.json()
                    transactions = details_data['data'].get('transactions', [])

                    if not transactions:
                        break

                    for day_data in transactions:
                        if day_data['date'] == today_date_json:
                            day_transactions = day_data['transactions']
                            replenishments = [trans for trans in day_transactions if
                                              'пополнение' in trans['description']['text'].lower()]
                            len_replenishments += len(replenishments)
                            break
                        else:
                            flag_page = False
                            break
                    if flag_page:
                        page += 1
                    else:
                        break
                else:
                    messages.append(f'Ошибка при получении данных о пополнении для {client_name}\n')
                    break
        if len_replenishments == 0:
            messages.append('\n')
        else:
            messages.append(
                f'Сегодня было пополнение баланса\n')
    except Exception as e:
        messages.append(f'Ошибка для {client_name}: {str(e)}\n')

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
                                     check_problems: bool = False, check_cause: bool = False, company=None) -> str:
    id_advertisement: str = advertisement['_id']
    chapter = advertisement['section']

    active_day_map: Dict[str, set] = is_day_active()
    active_day: Optional[set] = active_day_map.get(advertisement['active'], None)

    if active_day is None:
        logger.warning(
            f"Активный день для объявления '{id_advertisement}' не найден. Пожалуйста, добавьте его в active_day_map.")
        return f'Для объявления "{id_advertisement}" активный день не определён. Требуется обновление.\n\n'

    is_active_day: bool = current_day in active_day
    url: str = static.Urls.URL_ADVERTISEMENT.get_url(id_advertisement=id_advertisement)

    start_time = datetime.strptime(advertisement['start'].strip(), '%H.%M').time()
    end_time = datetime.strptime(advertisement['finish'].strip(), '%H.%M').time()

    if check_problems:
        if check_cause:
            boobs = load_table.companies[company]['Boobs']
            headers = {'Cookie': f"boobs={boobs}"}
            balance_url = static.Urls.BALANCE_URL.value
            async with aiohttp.request('get', balance_url, headers=headers, allow_redirects=False) as balance_response:
                if balance_response.status == 200:
                    balance_data = await balance_response.json()
                    balance = balance_data.get('canSpend')
                else:
                    return f'Ошибка получения баланса для {company}\n'
            if not (id_advertisement in all_dict) and (
                    start_time <= vladivostok_time <= end_time) and is_active_day and balance >= 150:
                return f'URL: {url}\nОбъявление не приклеено\nАктивные часы: {advertisement["start"].strip()} - {advertisement["finish"].strip()}\n\n'
            elif id_advertisement in all_dict and (
                    not (start_time <= vladivostok_time <= end_time) or not is_active_day):
                return f'URL: {url}\nОбъявление приклеено\nАктивные часы: {advertisement["start"].strip()} - {advertisement["finish"].strip()}\n\n'
            else:
                return ''
        else:
            if id_advertisement in all_dict and (not (start_time <= vladivostok_time <= end_time) or not is_active_day):
                return f'URL: {url}\nОбъявление приклеено\nАктивные часы: {advertisement["start"].strip()} - {advertisement["finish"].strip()}\n\n'
            elif not (id_advertisement in all_dict) and (start_time <= vladivostok_time <= end_time) and is_active_day:
                return f'URL: {url}\nОбъявление не приклеено\nАктивные часы: {advertisement["start"].strip()} - {advertisement["finish"].strip()}\n\n'
            else:
                return ''
    else:
        if id_advertisement in all_dict and (start_time <= vladivostok_time <= end_time) and is_active_day:
            currencies = all_dict[id_advertisement]["currencies"].split(',')
            return f'URL: https://www.farpost.ru/{id_advertisement}\nРаздел: {chapter}\n{currencies[0]}: {currencies[1]}\n\n'
        elif id_advertisement in all_dict and (
                not (start_time <= vladivostok_time <= end_time) or not is_active_day):
            return f'Для объявления "{url}" время вышло, но оно присутствует\n\n'
        elif not (id_advertisement in all_dict) and (
                start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'Для объявления "{url}" время не вышло, но его нет\n\n'
        else:
            return f'Для объявления "{url}" вышло время\n\n'


async def load_advertisements_data(company_name: str, company_boobs: str) -> Union[Dict[str, Dict[str, str]], str]:
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

                cards_advertisement = soup.find_all('tr', class_='bull-list-item-js')

                if not cards_advertisement:
                    break

                for card in cards_advertisement:
                    title = card.find('a', class_='bulletinLink bull-item__self-link auto-shy')
                    currency = card.find('div', class_='service-card-head__link serviceStick applied')
                    if currency:
                        page_data = {
                            re.search(r'(\d+)\.html', title['href']).group(1):
                                {
                                    'currencies': currency.text.strip(),
                                    'name': title.text.strip()
                                }
                        }
                        all_dict.update(page_data)
                    else:
                        continue

                page += 1
            elif response.status == 303:
                break
            else:
                return company_name
    return all_dict


async def handle_advertisements(callback: types.CallbackQuery, company_name: str, is_problem: bool):
    company_boobs = load_table.companies[company_name].get('Boobs', '')

    if not company_boobs:
        await callback.message.answer(static.Message.ERROR_COMMAND.value)
        await callback.answer()
        return

    await callback.message.answer(static.Message.LOAD_COMMAND.value)
    all_dict = await load_advertisements_data(company_name, company_boobs)

    if isinstance(all_dict, str):
        message = f'<b>Компания "{company_name}"</b>\n\nОшибка получения данных'
        await callback.message.answer(message, parse_mode='HTML')
    else:
        company_advertisements = load_table.advertisements[company_name]
        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        vladivostok_time = datetime.now(vladivostok_tz).time()
        current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

        tasks = [
            fetch_advertisement_common(advertisement, all_dict, vladivostok_time, current_day_vladivostok, is_problem)
            for advertisement in company_advertisements
            if advertisement['status'] == 'Подключено'
        ]

        message_list = []
        messages = [f'<b>{company_name}</b>\n\n']
        message_lines = await asyncio.gather(*tasks)
        for text in message_lines:
            if len(''.join(messages)) + len(text) > 4096:
                message_list.append(''.join(messages))
                messages = []

            messages.append(text)

        if messages:
            message_list.append(''.join(messages))

        for part in message_list:
            await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()


async def execute_ssh_command(command: str) -> tuple:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(static.SshData.IP.value, username=static.SshData.USERNAME.value,
                    password=dotenv_values(".env")['PASSWORD_SSH'])

        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        return output, error

    except AuthenticationException:
        return "", "Ошибка аутентификации: неверный логин или пароль."
    except SSHException as e:
        return "", f"Ошибка SSH соединения: {str(e)}"
    except Exception as e:
        return "", f"Ошибка при подключении: {str(e)}"
    finally:
        ssh.close()


async def get_service_logs() -> tuple:
    log_command = 'journalctl -u 100_cctv.service -n 5'
    return await execute_ssh_command(log_command)


async def fetch_data_for_advertisement(advertisements) -> Union[dict, str]:
    company_boobs = load_table.companies[advertisements['client']].get('Boobs', '')
    if company_boobs:
        headers = {'Cookie': f'boobs={company_boobs}'}
        base_url = static.Urls.URL_ACTUAL_BULLETINS.value
        page = 1
        all_dict = {}

        company_data = {}

        while True:
            url = f"{base_url}?page={page}"
            async with aiohttp.request('get', url, headers=headers, allow_redirects=False) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')

                    cards_advertisement = soup.find_all('tr', class_='bull-list-item-js')

                    if not cards_advertisement:
                        break

                    for card in cards_advertisement:
                        title = card.find('a', class_='bulletinLink bull-item__self-link auto-shy')
                        currency = card.find('div', class_='service-card-head__link serviceStick applied')
                        if currency:
                            page_data = {
                                re.search(r'(\d+)\.html', title['href']).group(1):
                                    {
                                        'currencies': currency.text.strip(),
                                        'name': title.text.strip()
                                    }
                            }
                            all_dict.update(page_data)
                        else:
                            continue

                    page += 1
                elif response.status == 303:
                    break
                else:
                    return f'Ошибка получения данных для "{advertisements["client"]}"\n\n'

        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        vladivostok_time = datetime.now(vladivostok_tz).time()
        current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

        task = await fetch_advertisement_common(
            advertisements, all_dict, vladivostok_time, current_day_vladivostok, False
        )

        company_data[advertisements["client"]] = task

        return company_data
    else:
        return f'Для компании "{advertisements["client"]} - {advertisements["city"]}" действие недоступно\n\n'


async def problems_advertisements_balance(balance_url, boobs, company):
    headers = {'Cookie': f"boobs={boobs}"}
    async with aiohttp.request('get', balance_url, headers=headers, allow_redirects=False) as balance_response:
        if balance_response.status == 200:
            balance_data = await balance_response.json()
            balance = balance_data.get('canSpend')
            return {company: f"Баланс: {balance} ₽"}
        else:
            return {company: "Ошибка получения баланс"}


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
    merged_dict = {}
    error_companies = []

    for result in all_dict:
        if isinstance(result, dict):
            merged_dict.update(result)
        elif isinstance(result, str):
            error_companies.append(result)

    company_messages = {}

    for company, list_advertisements in advertisements.items():
        if company in [error for error in error_companies]:
            company_messages[company] = ["Ошибка загрузки данных для компании\n"]
            continue

        if companies[company].get('Boobs', ''):
            task_result = [
                fetch_advertisement_common(advertisement, merged_dict, vladivostok_time, current_day_vladivostok,
                                           check_problems=True)
                for advertisement in list_advertisements
                if advertisement['status'] == 'Подключено'
            ]

            company_message_lines = await asyncio.gather(*task_result)

            filtered_messages = [msg for msg in company_message_lines if msg]
            if filtered_messages:
                company_messages[company] = filtered_messages

    balance_url = static.Urls.BALANCE_URL.value
    task_balance = [problems_advertisements_balance(balance_url, load_table.companies[company]['Boobs'], company) for
                    company in
                    company_messages]

    balances = await asyncio.gather(*task_balance)

    merged_balances = {key: value for d in balances for key, value in d.items()}

    message = ''
    for company, messages in company_messages.items():
        message += f'{company}:\n{merged_balances[company]}\n\n'
        message += ''.join(messages)
        message += "\n"

    return message


async def fetch_advertisement_stats(id_advertisement, boobs, current_date, section):
    url = static.Urls.URL_STATISTIC.get_url(ad_id=id_advertisement, current_date=current_date)
    headers = {'Cookie': f'boobs={boobs}'}

    async with aiohttp.request('get', url, headers=headers, allow_redirects=False) as response:
        if response.status == 200:
            data_json = await response.json()
            data = data_json['data']

            if isinstance(data, list):
                cnt = 0
                contactsCount = 0
                jobResponses = 0
                bookmarked = 0
                transactions = 0
            else:
                cnt = data.get('count', '')
                if not cnt:
                    cnt = 0
                else:
                    cnt = cnt[current_date]

                if section != 'Вакансии':
                    contactsCount = data.get('contactsCount', '')
                    if not contactsCount:
                        contactsCount = 0
                    else:
                        contactsCount = contactsCount[current_date]
                else:
                    contactsCount = None

                if section == 'Вакансии':
                    jobResponses = data.get('jobResponses', '')
                    if not jobResponses:
                        jobResponses = 0
                    else:
                        jobResponses = jobResponses[current_date]
                else:
                    jobResponses = None

                bookmarked = data.get('bookmarked', '')
                if not bookmarked:
                    bookmarked = 0
                else:
                    bookmarked = bookmarked[current_date]

                transactions = data.get('transactions', '')
                if not transactions:
                    transactions = 0
                else:
                    transactions = Decimal(transactions[current_date]).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)

            return {
                id_advertisement: {
                    'Просмотр объявлений': cnt,
                    **({'Просмотр контактов': contactsCount} if contactsCount is not None else {}),
                    'Добавлений в избранное': bookmarked,
                    **({'Отклик': jobResponses} if jobResponses is not None else {}),
                    'Платные операции': transactions
                }
            }
        else:
            return 'Ошибка получения данных'


async def send_statistics_to_users(bot):
    companies = load_table.companies
    advertisements = load_table.advertisements

    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    current_date = datetime.now(vladivostok_tz).strftime('%Y-%m-%d')

    statistics_info = {}

    for company, list_advertisement in advertisements.items():
        tasks = []
        for advertisement in list_advertisement:
            if advertisement['status'] == 'Подключено':
                id_advertisement = advertisement['_id']
                boobs = companies[company]['Boobs']

                task = fetch_advertisement_stats(id_advertisement, boobs, current_date, advertisement['section'])
                tasks.append(task)

        stat_company = await asyncio.gather(*tasks)

        statistics_info[company] = stat_company

    for company, list_data in statistics_info.items():
        total_sums = {}
        lines = list()
        lines.append(f'{company} ({current_date}):\n')

        for data_dict in list_data:
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
            if companies[company]['Chat_id'] == '-':
                continue
            parts = split_message(text)
            chats_id = companies[company]['Chat_id'].split('\n')
            for chat_id in chats_id:
                for part in parts:
                    await bot.send_message(chat_id=chat_id, text=part)
        except aiogram.exceptions.TelegramBadRequest:
            logger.error(f'Бот не может отправить "{company}" сообщение по данным статистики объявлений')
            continue


async def repeat_send_problems_advertisements(bot, chats_idx):
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    vladivostok_time = datetime.now(vladivostok_tz).time()

    current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

    advertisements = load_table.advertisements
    companies = load_table.companies

    task_all_dict = [
        load_advertisements_data(company, companies[company].get('Boobs', ''))
        for company in advertisements
        if companies[company].get('Boobs', '') and company != 'Напарили ДВ'
    ]

    all_dict = await asyncio.gather(*task_all_dict)
    merged_dict = {}
    error_companies = []

    for result in all_dict:
        if isinstance(result, dict):
            merged_dict.update(result)
        elif isinstance(result, str):
            error_companies.append(result)

    company_messages = {}

    for company, list_advertisements in advertisements.items():
        if company == 'Напарили ДВ':
            continue

        if company in [error for error in error_companies]:
            company_messages[company] = ["Ошибка загрузки данных для компании\n"]
            continue

        if companies[company].get('Boobs', ''):
            task_result = [
                fetch_advertisement_common(advertisement, merged_dict, vladivostok_time, current_day_vladivostok, True,
                                           True, company)
                for advertisement in list_advertisements
                if advertisement['status'] == 'Подключено' and
                   advertisement['start'].strip() != vladivostok_time.strftime("%-H.%M") and
                   advertisement['finish'].strip() != vladivostok_time.strftime("%-H.%M") and advertisement[
                       '_id'] not in ['58237112', '61797382', '118160752', '119696095', '58917863', '117802456',
                                      '110552257', '119697381', '117497197', '117497287', '118042311', '117462211',
                                      '117462016']
            ]

            company_message_lines = await asyncio.gather(*task_result)

            filtered_messages = [msg for msg in company_message_lines if msg]
            if filtered_messages:
                company_messages[company] = filtered_messages

    balance_url = static.Urls.BALANCE_URL.value
    task_balance = [problems_advertisements_balance(balance_url, load_table.companies[company]['Boobs'], company) for
                    company in
                    company_messages]

    balances = await asyncio.gather(*task_balance)

    merged_balances = {key: value for d in balances for key, value in d.items()}

    message = ''
    for company, messages in company_messages.items():
        message += f'{company}:\n{merged_balances[company]}\n\n'
        message += ''.join(messages)
        message += "\n"

    if not message:
        message = 'Для компаний нет "проблемных" объявлений по заданным условиям'

    parts = split_message(message)

    for chat_id in chats_idx:
        for part in parts:
            await bot.send_message(chat_id=chat_id, text=part)


async def statistics_to_users_friday():
    companies = load_table.companies
    advertisements = load_table.advertisements

    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    current_date = datetime.now(vladivostok_tz)

    dates_last_week = [(current_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]

    statistics_info = {}

    for company, list_advertisement in advertisements.items():
        statistics_info[company] = {}
        for advertisement in list_advertisement:
            if advertisement['status'] == 'Подключено':
                id_advertisement = advertisement['_id']
                boobs = companies[company]['Boobs']

                tasks = []
                for date in dates_last_week:
                    task = fetch_advertisement_stats(id_advertisement, boobs, date, advertisement['section'])
                    tasks.append((date, task))

                stat_advertisement = await asyncio.gather(*[task for _, task in tasks])
                statistics_info[company][id_advertisement] = {}

                for (date, _), result in zip(tasks, stat_advertisement):
                    statistics_info[company][id_advertisement][date] = result

    summarized_info = defaultdict(lambda: defaultdict(lambda: {
        'Просмотр объявлений': 0,
        'Просмотр контактов': 0,
        'Добавлений в избранное': 0,
        'Отклик': 0,
        'Платные операции': Decimal('0.0')
    }))

    for company, ads in statistics_info.items():
        for ad_id, dates in ads.items():
            for date, stats in dates.items():
                if isinstance(stats, dict):
                    ad_stats = stats[ad_id]
                    summarized_info[company][ad_id]['Просмотр объявлений'] += int(
                        ad_stats.get('Просмотр объявлений', 0))
                    if ad_stats.get('Просмотр контактов') is None:
                        summarized_info[company][ad_id]['Просмотр контактов'] = -1
                    else:
                        summarized_info[company][ad_id]['Просмотр контактов'] += int(ad_stats.get('Просмотр контактов'))
                    summarized_info[company][ad_id]['Добавлений в избранное'] += int(
                        ad_stats.get('Добавлений в избранное', 0))
                    if ad_stats.get('Отклик') is None:
                        summarized_info[company][ad_id]['Отклик'] = -1
                    else:
                        summarized_info[company][ad_id]['Отклик'] += int(ad_stats.get('Отклик'))
                    summarized_info[company][ad_id]['Платные операции'] += Decimal(
                        ad_stats.get('Платные операции', '0.0'))
                elif isinstance(stats, str):
                    logger.error(f'Для {company} - {ad_id} произошла ошибка')
                    continue

    return summarized_info, dates_last_week[-1], dates_last_week[0]


async def send_statistics_to_users_friday(bot):
    summarized_info, day_start, day_finish = await statistics_to_users_friday()
    messages = {}
    for company, ads in summarized_info.items():
        company_messages = [f'<b>{company} (с {day_start} по {day_finish})</b>\n\n']
        for ad_id, totals in ads.items():
            company_messages.append(f'URL: https://www.farpost.ru/{ad_id}\n')
            for criteria, total in totals.items():
                if total == -1:
                    continue
                company_messages.append(f'{criteria}: {total}\n')
            company_messages.append('\n')
        messages[company] = ''.join(company_messages)

    for company in messages:
        try:
            if load_table.companies[company]['Chat_id'] == '-':
                continue
            chats_id = load_table.companies[company]['Chat_id'].split('\n')
            for chat_id in chats_id:
                await bot.send_message(chat_id=chat_id, text=messages[company], parse_mode='HTML')
        except aiogram.exceptions.TelegramBadRequest:
            logger.error(f'Бот не может отправить "{company}" сообщение по данным статистики объявлений')
            continue


async def repeat_send_position_advertisements(bot, chats_idx, position_advertisements):
    result = await position(position_advertisements)

    company_result = forming_position(result)

    if not company_result:
        for chat_id in chats_idx:
            await bot.send_message(chat_id=chat_id, text="Нет данных о позициях.")
        return

    message_list = ['<b>Позиции объявлений\n\n</b>']
    message_current_list = []
    result_message_list = []

    for client, ads in company_result.items():
        if client in load_table.balance_position:
            if isinstance(load_table.balance_position[client], str):
                continue
            if load_table.balance_position[client] <= 150:
                continue

        message_current_list.append(f'<b>{client}:</b>\n')
        for ad_id, status in ads.items():
            message_current_list.append(f'URL: https://www.farpost.ru/{ad_id}\nОбъявление <b>{status}</b>\n\n')
        message_current_list.append('\n')
        if len(''.join(message_list)) + len(''.join(message_current_list)) >= 4096:
            result_message_list.append(''.join(message_list))
            message_list = []
        message_list.append(''.join(message_current_list))
        message_current_list = []

    result_message_list.append(''.join(message_list))

    for chat_id in chats_idx:
        for part in result_message_list:
            await bot.send_message(chat_id=chat_id, text=part, parse_mode='HTML')


async def slow_repeat_send_position_advertisements(bot, chats_idx, position_advertisements):
    result = await position(position_advertisements)

    company_result = forming_position(result)

    if not company_result:
        for chat_id in chats_idx:
            await bot.send_message(chat_id=chat_id, text='Нет данных о позициях с параметром "is_slow".')
        return

    message_list = ['<b>Позиции объявлений с параметром "is_slow"\n\n</b>']
    message_current_list = []
    result_message_list = []

    for client, ads in company_result.items():
        if client in load_table.balance_position:
            if isinstance(load_table.balance_position[client], str):
                continue
            if load_table.balance_position[client] <= 150:
                continue

        message_current_list.append(f'<b>{client}:</b>\n')
        for ad_id, status in ads.items():
            message_current_list.append(f'URL: https://www.farpost.ru/{ad_id}\nОбъявление <b>{status}</b>\n\n')
        message_current_list.append('\n')
        if len(''.join(message_list)) + len(''.join(message_current_list)) >= 4096:
            result_message_list.append(''.join(message_list))
            message_list = []
        message_list.append(''.join(message_current_list))
        message_current_list = []

    result_message_list.append(''.join(message_list))

    for chat_id in chats_idx:
        for part in result_message_list:
            await bot.send_message(chat_id=chat_id, text=part, parse_mode='HTML')


async def fetch_url(url, cookies, headers):
    async with aiohttp.ClientSession(cookies=cookies, headers=headers) as session:
        async with session.post(url) as response:
            if response.status == 200:
                return await response.json()
            return {"error": f"Request failed with status {response.status}"}


async def position(position_advertisements):
    position_advertisements = position_advertisements
    base_url = "https://www.farpost.ru/api/1.0/rate/stick-order-keys"
    cookies = {
        "boobs": "v4.local.97tIvFnOqoJnuZpltEhNdijYvX-yXWsNqKZDYunaEjZ2l8msd0S23OnO6F3rTwV-WElEugzEGxkxgm7M6MHk680Kcg0R9zd2-R6jML5Zxvyo7OCcew26DbJI7GvmTqwp2E-xPxFOqpG8cTb3bMkpyqokN1JOqGZKf0OWlCMUkxUKxtpD1rb4y1hWqqjM1yU1NftfgqU-IlaeAHAoZczAAX1aoVl51o8.eyJ1c2VySWQiOjMyNTYyMzI3fQ.u1f0dc97",
        "ring": "9a5680d6f1193cccf046602f5d4b5025",
    }
    headers = {
        "User-Agent": UserAgent().random,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.farpost.ru",
    }

    for params in position_advertisements:
        geo_ad, lemma_ad, dir_ad = params
        query_params = f"?bulletin=11111111&dirId={dir_ad}&geoId={geo_ad}&lemma={lemma_ad}"
        url = base_url + query_params

        try:
            response = await fetch_url(url, cookies, headers)
            res_list = []

            for content in response:
                pattern = r"FR60A:0(\d+)\.00"
                match = re.search(pattern, content)

                if match:
                    result = int(match.group(1)) - 10000
                    res_list.append(result)

            res_list.sort(reverse=True)

            position_advertisements[params]["price"] = res_list
        except Exception as e:
            print("Error:", e)

        await asyncio.sleep(random.uniform(5, 10))

    result = {}

    for key, value in position_advertisements.items():
        for idx, ad_id in enumerate(value["idx"]):
            result[ad_id] = value["price"]

    return result


def forming_position(result):
    company_result = {}

    for idx, price in result.items():
        start_time = datetime.strptime(load_table.info_for_id_ad[idx][0]['start'].strip(), '%H.%M').time()
        end_time = datetime.strptime(load_table.info_for_id_ad[idx][0]['finish'].strip(), '%H.%M').time()

        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        vladivostok_time = datetime.now(vladivostok_tz).time()

        if vladivostok_time >= end_time or vladivostok_time <= start_time:
            continue

        limit = int(load_table.info_for_id_ad[idx][0]["limit"]) + int(load_table.info_for_id_ad[idx][0]["step"])

        for i, price_value in enumerate(price):
            if price_value <= limit:
                new_price = price[i:]
                break
        else:
            new_price = []

        position_ad_table = int(load_table.info_for_id_ad[idx][0]["position"])
        if len(new_price) >= position_ad_table:
            cent = new_price[position_ad_table - 1]
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

    return company_result


async def send_position(message, company_result, is_slow):
    if not company_result:
        await message.answer("Нет данных о позициях.")
        return

    if is_slow:
        message_list = ['<b>Позиции объявлений с параметром "is_slow"\n\n</b>']
    else:
        message_list = ['<b>Позиции объявлений\n\n</b>']

    message_current_list = []
    result_message_list = []

    for client, ads in company_result.items():
        if client in load_table.balance_position:
            if isinstance(load_table.balance_position[client], str):
                continue
            if load_table.balance_position[client] <= 150:
                continue

        message_current_list.append(f'<b>{client}:</b>\n')
        for ad_id, status in ads.items():
            message_current_list.append(f'URL: https://www.farpost.ru/{ad_id}\nОбъявление <b>{status}</b>\n\n')
        message_current_list.append('\n')
        if len(''.join(message_list)) + len(''.join(message_current_list)) >= 4096:
            result_message_list.append(''.join(message_list))
            message_list = []
        message_list.append(''.join(message_current_list))
        message_current_list = []

    result_message_list.append(''.join(message_list))

    for part in result_message_list:
        await message.answer(text=part, parse_mode='HTML')


async def send_payments_day():
    payments = {}

    companies = load_table.companies
    for company, data_dict in companies.items():
        if company == 'IT-solutions':
            continue
        date_str = data_dict["Next payment day"]

        date_format = '%d.%m.%Y'
        next_payment_date = datetime.strptime(date_str, date_format).date()

        vladivostok_tz = pytz.timezone('Asia/Vladivostok')
        current_date_vladivostok = datetime.now(vladivostok_tz).date()

        if (current_date_vladivostok + timedelta(days=1)) == next_payment_date:
            payments[company] = {
                'Клиент': data_dict['Client'],
                'Телефон': data_dict['Phone number'],
                'Дата платежа': data_dict['Next payment day'],
                'Сумма платежа': data_dict['How much is paid'],
                'Сообщение': 'Завтра необходимо оплатить'
            }
        elif current_date_vladivostok == next_payment_date:
            payments[company] = {
                'Клиент': data_dict['Client'],
                'Телефон': data_dict['Phone number'],
                'Дата платежа': data_dict['Next payment day'],
                'Сумма платежа': data_dict['How much is paid'],
                'Сообщение': 'Сегодня необходимо оплатить'
            }
        elif (current_date_vladivostok - next_payment_date).days > 0:
            payments[company] = {
                'Клиент': data_dict['Client'],
                'Телефон': data_dict['Phone number'],
                'Дата платежа': data_dict['Next payment day'],
                'Сумма платежа': data_dict['How much is paid'],
                'Сообщение': f"Задолжность платежа {(current_date_vladivostok - next_payment_date).days} дней"
            }

    return payments


async def message_payments_day(bot, chats_idx):
    res_payment = await send_payments_day()

    message_list = []

    message_current_list = []
    result_message_list = []

    for company, data_dict in res_payment.items():
        message_current_list.append(f'<b>{company}:</b>\n')
        for filed, data in data_dict.items():
            message_current_list.append(f"<b>{filed}:</b> {data}\n")
        message_current_list.append('\n')
        if len(''.join(message_list)) + len(''.join(message_current_list)) >= 4096:
            result_message_list.append(''.join(message_list))
            message_list = []
        message_list.append(''.join(message_current_list))
        message_current_list = []

    result_message_list.append(''.join(message_list))

    for chat_id in chats_idx:
        for part in result_message_list:
            await bot.send_message(chat_id=chat_id, text=part, parse_mode='HTML')
