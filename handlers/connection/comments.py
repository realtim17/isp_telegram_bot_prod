"""Шаг комментария."""
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import ENTER_COMMENT
from utils.keyboards import get_main_keyboard
from handlers.connection.ui import build_reply_keyboard, SKIP_TEXT, CANCEL_TEXT as BUTTON_CANCEL_TEXT
from handlers.connection.constants import CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.executors import start_employee_selection

CANCEL_TEXT_VARIANTS = tuple(
    text for text in (BUTTON_CANCEL_TEXT, LEGACY_CANCEL_TEXT) if text
)


async def start_comment_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Отправить пользователю шаг ввода комментария."""
    context.user_data.setdefault('connection_data', {})

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return ENTER_COMMENT

    message_text = (
        "💬 <b>Шаг 15/16: Комментарий</b>\n\n"
        "Оставьте комментарий по подключению (сложности, нюансы, потраченные материалы и т.д.).\n"
        "Если комментарий не нужен, нажмите \"Пропустить\"."
    )
    reply_markup = build_reply_keyboard([[SKIP_TEXT]], add_cancel=True)

    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

    return ENTER_COMMENT


async def enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()

    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['comment'] = "-" if text == SKIP_TEXT or not text else text

    confirm_text = (
        "💬 <b>Шаг 15/16: Комментарий</b>\n\n"
        "✅ Комментарий сохранен."
    )
    if text == SKIP_TEXT or not text:
        confirm_text = (
            "💬 <b>Шаг 15/16: Комментарий</b>\n\n"
            "⏭️ Комментарий пропущен."
        )
    await update.message.reply_text(confirm_text, reply_markup=ReplyKeyboardRemove(), parse_mode='HTML')

    return await start_employee_selection(update, context, db)
