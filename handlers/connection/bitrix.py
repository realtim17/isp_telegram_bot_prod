"""Шаг ввода ссылки на задачу в Bitrix24."""
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import ENTER_BITRIX_TASK_LINK
from handlers.connection.constants import CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.ui import (
    build_reply_keyboard,
    SKIP_TEXT,
    CANCEL_TEXT as BUTTON_CANCEL_TEXT,
)
from utils.keyboards import get_main_keyboard


CANCEL_TEXT_VARIANTS = tuple(
    text for text in (BUTTON_CANCEL_TEXT, LEGACY_CANCEL_TEXT) if text
)


async def start_bitrix_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Показать шаг ввода ссылки на задачу Bitrix24."""
    message = update.effective_message
    if not message:
        return ENTER_BITRIX_TASK_LINK

    await message.reply_text(
        "🔗 <b>Шаг 4/20: Ссылка на задачу в Bitrix24</b>\n\n"
        "Введите ссылку на задачу или нажмите «Пропустить».\n\n"
        "⚠️ Пропускать только если задача отсутствует в Bitrix24.",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return ENTER_BITRIX_TASK_LINK


async def enter_bitrix_task_link(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Сохранить ссылку на задачу Bitrix24 и перейти к шагу роутера."""
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    context.user_data.setdefault("connection_data", {})

    if text == SKIP_TEXT:
        context.user_data["connection_data"]["bitrix_task_url"] = "-"
        await update.message.reply_text(
            "🔗 <b>Шаг 4/20: Ссылка на задачу в Bitrix24</b>\n\n⏭️ Пропущено.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )
    else:
        context.user_data["connection_data"]["bitrix_task_url"] = text
        await update.message.reply_text(
            "🔗 <b>Шаг 4/20: Ссылка на задачу в Bitrix24</b>\n\n"
            f"✅ Ссылка сохранена:\n{text}",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML",
        )

    from handlers.connection.devices import start_router_step
    address = context.user_data.get("connection_data", {}).get("address", "")
    return await start_router_step(update, context, db, address=address)
