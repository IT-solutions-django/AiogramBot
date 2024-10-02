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

import logging

import locale

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_day_active() -> Dict[str, set]:
    weekdays = {0, 1, 2, 3, 4}
    all_days_except_sunday = {0, 1, 2, 3, 4, 5}
    full_week = {0, 1, 2, 3, 4, 5, 6}

    day_info_map = {
        'Будни': weekdays,
        'Кроме ВС': all_days_except_sunday,
        'Все': full_week,
    }

    return day_info_map


MAX_MESSAGE_LENGTH: int = 4096


def split_message(text: str) -> List[str]:
    return [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]


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

    today_date = datetime.now().strftime('%Y-%m-%d')
    today_date_json = datetime.now().strftime('%-d %B')

    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer('Идет загрузка баланса...')
    else:
        await obj.answer('Идет загрузка баланса...')

    async with aiohttp.ClientSession() as session:
        tasks = []
        for client_name, boob_value in boobs.items():
            headers = {'Cookie': f"boobs={boob_value['Boobs']}"}
            balance_url = f'https://www.farpost.ru/personal/checkBalance/'
            details_url = f'https://www.farpost.ru/personal/balance/details?date={today_date}&page=1'

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
                messages.append(f'Ошибка при получении данных о пополнении для {client_name}')
    except Exception as e:
        messages.append(f'Ошибка для {client_name}: {str(e)}')

    return '\n'.join(messages)


async def get_server(obj: Union[types.CallbackQuery, types.Message]) -> None:
    buttons_command_server = [
        [types.InlineKeyboardButton(text='Start', callback_data='start')],
        [types.InlineKeyboardButton(text='Stop', callback_data='stop')],
        [types.InlineKeyboardButton(text='Restart', callback_data='restart')],
        [types.InlineKeyboardButton(text='Status', callback_data='status')]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons_command_server)
    if isinstance(obj, types.CallbackQuery):
        await obj.message.answer(text='Выберите команду', reply_markup=keyboard)
        await obj.answer()
    else:
        await obj.answer(text='Выберите команду', reply_markup=keyboard)


async def fetch_advertisement_common(advertisement: Dict[str, str], all_dict: Dict[str, Dict[str, str]],
                                     vladivostok_time: time, current_day: int,
                                     check_problems: bool = False) -> str:
    id_advertisement: str = advertisement['_id']

    active_day_map: Dict[str, set] = is_day_active()
    active_day: Optional[set] = active_day_map.get(advertisement['weekday_active'], None)

    if active_day is None:
        logging.warning(
            f"Активный день для объявления '{id_advertisement}' не найден. Пожалуйста, добавьте его в active_day_map.")
        return f'Для объявления "{id_advertisement}" активный день не определён. Требуется обновление.\n\n'

    is_active_day: bool = current_day in active_day
    url: str = f'https://www.farpost.ru/{id_advertisement}/'

    start_time = datetime.strptime(advertisement['start_time'], '%H.%M').time()
    end_time = datetime.strptime(advertisement['finish_time'], '%H.%M').time()

    if check_problems:
        if id_advertisement in all_dict and (not (start_time <= vladivostok_time <= end_time) or not is_active_day):
            return f'Для объявления "{url}" время вышло, но оно присутствует. Необходимо проверить данную информацию\n\n'
        elif not (id_advertisement in all_dict) and (start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'Для объявления "{url}" время не вышло, но его нет. Необходимо проверить данную информацию\n\n'
        else:
            return ''
    else:
        if id_advertisement in all_dict and (start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'{all_dict[id_advertisement]['name']} - {all_dict[id_advertisement]['currencies']}\n\n'
        elif id_advertisement in all_dict and (
                not (start_time <= vladivostok_time <= end_time) or not is_active_day):
            return f'Для объявления "{url}" время вышло, но оно присутствует. Необходимо проверить данную информацию\n\n'
        elif not (id_advertisement in all_dict) and (
                start_time <= vladivostok_time <= end_time) and is_active_day:
            return f'Для объявления "{url}" время не вышло, но его нет. Необходимо проверить данную информацию\n\n'
        else:
            return f'Для объявления "{url}" вышло время\n\n'


async def load_advertisements_data(company_name: str, company_boobs: str) -> Dict[str, Dict[str, str]]:
    headers = {'Cookie': f'boobs={company_boobs}'}
    url = 'https://www.farpost.ru/personal/actual/bulletins'
    async with aiohttp.request('get', url, headers=headers) as response:
        if response.status == 200:
            content = await response.text()
            soup = BeautifulSoup(content, 'html.parser')

            currencies = soup.find_all('div', class_='service-card-head__link serviceStick applied')
            titles = soup.find_all('a', class_='bulletinLink bull-item__self-link auto-shy')

            all_dict = {
                re.search(r'-(\d+)\.html', title['href']).group(1):
                    {
                        'currencies': div.text.strip().split(',')[1],
                        'name': title.text
                    }
                for title, div in zip(titles, currencies)
            }
            return all_dict
    return {}


async def handle_advertisements(callback: types.CallbackQuery, company_name: str, is_problem: bool):
    company_boobs = load_table.companies[company_name].get('Boobs', '')

    if not company_boobs:
        await callback.message.answer('Для данной компании действие недоступно')
        await callback.answer()
        return

    await callback.message.answer('Загружаем данные...')
    all_dict = await load_advertisements_data(company_name, company_boobs)

    company_advertisements = load_table.advertisements[company_name]
    vladivostok_tz = pytz.timezone('Asia/Vladivostok')
    vladivostok_time = datetime.now(vladivostok_tz).time()
    current_day_vladivostok = datetime.now(vladivostok_tz).weekday()

    tasks = [
        fetch_advertisement_common(advertisement, all_dict, vladivostok_time, current_day_vladivostok, is_problem)
        for advertisement in company_advertisements
    ]

    message_lines = await asyncio.gather(*tasks)
    message = ''.join(message_lines)

    if not message:
        message = 'Для данной компании нет "проблемных" объявлений' if is_problem else 'Нет объявлений'

    parts = split_message(message)
    for part in parts:
        await callback.message.answer(part, parse_mode='HTML')

    await callback.answer()
