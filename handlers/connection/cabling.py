"""Шаги, связанные с вводом порта и метража кабелей."""
from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import ENTER_PORT, ENTER_FIBER, ENTER_TWISTED, ROUTER_ACCESS
from utils.keyboards import get_main_keyboard
from handlers.connection.cancellation import cancel_connection
from handlers.connection.constants import CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.ui import (
    build_inline_keyboard,
    build_reply_keyboard,
    cancel_reply_keyboard,
    SKIP_TEXT,
    CANCEL_TEXT as BUTTON_CANCEL_TEXT,
)

CANCEL_TEXT_VARIANTS = tuple(
    text for text in (BUTTON_CANCEL_TEXT, LEGACY_CANCEL_TEXT) if text
)


async def router_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)

    context.user_data.setdefault('connection_data', {})
    if query.data == 'router_access_confirmed':
        context.user_data['connection_data']['router_access'] = True
        status_text = "🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n✅ Доступ получен"
    else:
        context.user_data['connection_data']['router_access'] = False
        status_text = "🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n⏭️ Пропущено"

    await query.edit_message_text(
        status_text,
        parse_mode='HTML'
    )
    await query.message.reply_text(
        "🔌 <b>Шаг 7/16: Номер порта</b>\n\n"
        "Введите номер порта или воспользуйтесь кнопкой \"Пропустить\":",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]]),
        parse_mode='HTML'
    )
    return ENTER_PORT


async def _send_fiber_prompt(message) -> None:
    await message.reply_text(
        "📏 <b>Шаг 8/16: Метраж ВОЛС</b>\n\n"
        "Введите количество метров ВОЛС (волоконно-оптической линии связи):",
        reply_markup=cancel_reply_keyboard(),
        parse_mode='HTML'
    )


async def enter_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == 'cancel_connection':
            return await cancel_connection(update, context)
        if query.data == 'port_skip':
            context.user_data.setdefault('connection_data', {})
            context.user_data['connection_data']['port'] = '-'
            await query.message.reply_text(
                "🔌 <b>Шаг 7/16: Номер порта</b>\n\n⏭️ Порт пропущен.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardRemove()
            )
            await _send_fiber_prompt(query.message)
            return ENTER_FIBER
        return ENTER_PORT

    port = (update.message.text or '').strip()
    if port in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    context.user_data.setdefault('connection_data', {})
    if port == SKIP_TEXT:
        context.user_data['connection_data']['port'] = '-'
        await update.message.reply_text(
            "🔌 <b>Шаг 7/16: Номер порта</b>\n\n⏭️ Порт пропущен.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        await _send_fiber_prompt(update.message)
        return ENTER_FIBER

    context.user_data['connection_data']['port'] = port
    await update.message.reply_text(
        f"🔌 <b>Шаг 7/16: Номер порта</b>\n\n✅ Порт: {port}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await _send_fiber_prompt(update.message)
    return ENTER_FIBER


async def enter_fiber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or '').strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    try:
        fiber = float(text.replace(',', '.'))
        if fiber < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)")
        return ENTER_FIBER

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['fiber_meters'] = fiber
    await update.message.reply_text(
        f"📏 <b>Шаг 8/16: Метраж ВОЛС</b>\n\n✅ ВОЛС: {fiber} м",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await update.message.reply_text(
        "📏 <b>Шаг 9/16: Метраж витой пары</b>\n\n"
        "Введите количество метров витой пары:",
        reply_markup=cancel_reply_keyboard(),
        parse_mode='HTML'
    )
    return ENTER_TWISTED


async def enter_twisted(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or '').strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    try:
        twisted = float(text.replace(',', '.'))
        if twisted < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)")
        return ENTER_TWISTED

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['twisted_pair_meters'] = twisted
    await update.message.reply_text(
        f"📏 <b>Шаг 9/16: Метраж витой пары</b>\n\n✅ Витая пара: {twisted} м",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    from handlers.connection.steps import start_snr_step

    return await start_snr_step(update, context, db)
