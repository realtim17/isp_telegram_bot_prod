"""
Утилиты для построения клавиатур в сценариях подключения
"""
from typing import Iterable, Sequence, Optional
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)

CANCEL_TEXT = "❌ Отмена"
CANCEL_CALLBACK = 'cancel_connection'
SKIP_TEXT = "⏭️ Пропустить"


def build_inline_keyboard(
    rows: Iterable[Sequence[InlineKeyboardButton]],
    add_cancel: bool = True
) -> InlineKeyboardMarkup:
    """Создать inline-клавиатуру с опциональной кнопкой отмены"""
    keyboard = [list(row) for row in rows]
    if add_cancel:
        keyboard.append([InlineKeyboardButton(CANCEL_TEXT, callback_data=CANCEL_CALLBACK)])
    return InlineKeyboardMarkup(keyboard)


def build_reply_keyboard(
    rows: Optional[Iterable[Sequence[str]]] = None,
    add_cancel: bool = True
) -> ReplyKeyboardMarkup:
    """Собрать ReplyKeyboardMarkup с указанными кнопками"""
    keyboard = []
    if rows:
        for row in rows:
            keyboard.append([KeyboardButton(label) for label in row])
    if add_cancel:
        keyboard.append([KeyboardButton(CANCEL_TEXT)])
    if not keyboard:
        keyboard = [[KeyboardButton(CANCEL_TEXT)]] if add_cancel else [[]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


def cancel_reply_keyboard(add_cancel: bool = True) -> ReplyKeyboardMarkup:
    """Сгенерировать reply-клавиатуру для отмены"""
    return build_reply_keyboard(add_cancel=add_cancel)
