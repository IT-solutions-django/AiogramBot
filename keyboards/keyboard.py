from aiogram import types

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

buttons_command_server = [
    [types.InlineKeyboardButton(text='Start', callback_data='start')],
    [types.InlineKeyboardButton(text='Stop', callback_data='stop')],
    [types.InlineKeyboardButton(text='Restart', callback_data='restart')],
    [types.InlineKeyboardButton(text='Status', callback_data='status')]
]
