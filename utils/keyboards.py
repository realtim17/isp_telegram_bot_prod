"""
Модуль для создания клавиатур
"""
from contextvars import ContextVar
from telegram import ReplyKeyboardMarkup, KeyboardButton

# Храним, для какого пользователя сейчас формируется клавиатура, чтобы не пробрасывать флаг в каждый вызов
_CURRENT_USER_IS_ADMIN = ContextVar("_current_user_is_admin", default=False)


def set_main_keyboard_admin_mode(is_admin: bool) -> None:
    """Зафиксировать признак администратора для последующих вызовов get_main_keyboard в рамках обработки апдейта"""
    _CURRENT_USER_IS_ADMIN.set(bool(is_admin))


def get_main_keyboard(is_admin: bool | None = None) -> ReplyKeyboardMarkup:
    """
    Создать главную клавиатуру.
    Если is_admin не передан, используется флаг из контекстной переменной, установленный в middleware.
    """
    if is_admin is None:
        is_admin = _CURRENT_USER_IS_ADMIN.get()

    keyboard = [
        [KeyboardButton("📝 Новое подключение")],
        [KeyboardButton("📊 Сводный отчет"), KeyboardButton("📋 Список сотрудников МОЛ")],
    ]

    if is_admin:
        keyboard.extend(
            [
                [KeyboardButton("👥 Управление сотрудниками"), KeyboardButton("📦 Материалы и оборудование")],
            ]
        )

    keyboard.append([KeyboardButton("ℹ️ Помощь")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
