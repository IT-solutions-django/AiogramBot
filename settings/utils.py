from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import aiohttp

from bs4 import BeautifulSoup

from datetime import datetime

MAX_MESSAGE_LENGTH = 4096


def split_message(text: str) -> list:
    return [text[i:i + MAX_MESSAGE_LENGTH] for i in range(0, len(text), MAX_MESSAGE_LENGTH)]


async def show_options(callback: types.CallbackQuery, data_dict: dict, exclude_key: str, action=None):
    builder = InlineKeyboardBuilder()
    for key in data_dict.keys():
        if action is not None:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=f'{action}_{key}'))
        else:
            builder.row(types.InlineKeyboardButton(text=key, callback_data=key))
    await callback.message.answer(text=f'Выберите {exclude_key}', reply_markup=builder.as_markup())
    await callback.answer()


async def fetch_advertisement_data(advertisement: dict, all_dict: dict, vladivostok_time) -> str:
    id_advertisement = advertisement['_id']
    url = f'https://www.farpost.ru/{id_advertisement}/'

    async with aiohttp.request('get', url, allow_redirects=True) as response:
        if response.status == 200:
            start_time = datetime.strptime(advertisement['start_time'], '%H.%M').time()
            end_time = datetime.strptime(advertisement['finish_time'], '%H.%M').time()

            if str(response.url) in all_dict and (start_time <= vladivostok_time <= end_time):
                content = await response.text()
                soup = BeautifulSoup(content, 'html.parser')
                title = soup.find('span', class_='inplace auto-shy')
                return f'{title.text} - {all_dict[str(response.url)]}\n\n'
            elif str(response.url) in all_dict and not (start_time <= vladivostok_time <= end_time):
                return f'Для объявления "{url}" время вышло, но оно присутствует. Необходимо проверить данную информацию\n\n'
            elif not (str(response.url) in all_dict) and (start_time <= vladivostok_time <= end_time):
                return f'Для объявления "{url}" время не вышло, но его нет. Необходимо проверить данную информацию\n\n'
            elif not (str(response.url) in all_dict) and not (start_time <= vladivostok_time <= end_time):
                return f'Для объявления "{url}" вышло время\n\n'
        else:
            return f'Для компании с id "{id_advertisement}" произошла ошибка запроса\n\n'
