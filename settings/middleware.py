from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable


class AccessMiddleware(BaseMiddleware):
    def __init__(self, allowed_chat_ids):
        super().__init__()
        self.allowed_chat_ids = allowed_chat_ids

    async def __call__(self,
                       handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
                       event: Update,
                       data: Dict[str, Any]) -> Any:
        if isinstance(event, Message):
            if event.from_user.id not in self.allowed_chat_ids:
                await event.answer("У вас есть только пользовательский доступ к боту.")
                return

        elif isinstance(event, CallbackQuery):
            if event.from_user.id not in self.allowed_chat_ids:
                await event.answer("У вас есть только пользовательский доступ к боту.", show_alert=True)
                return

        return await handler(event, data)
