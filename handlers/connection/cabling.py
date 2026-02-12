"""Шаги, связанные с вводом порта и метража кабелей."""
import re

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    ENTER_ACCOUNT_NUMBER,
    ENTER_PORT,
    ENTER_FIBER,
    ENTER_TWISTED,
    ENTER_TWISTED_INTERNAL,
    ROUTER_ACCESS,
)
from utils.keyboards import get_main_keyboard
from handlers.connection.cancellation import cancel_connection
from handlers.connection.constants import CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.ui import (
    build_reply_keyboard,
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
        status_text = "🔐 <b>Шаг 7/20: Доступ на роутер</b>\n\n✅ Доступ получен"
    else:
        context.user_data['connection_data']['router_access'] = False
        status_text = "🔐 <b>Шаг 7/20: Доступ на роутер</b>\n\n⏭️ Пропущено"

    await query.edit_message_text(
        status_text,
        parse_mode='HTML'
    )
    await _send_account_number_prompt(query.message)
    return ENTER_ACCOUNT_NUMBER


async def _send_fiber_prompt(message) -> None:
    await message.reply_text(
        "📏 <b>Шаг 10/20: Метраж ВОЛС</b>\n\n"
        "Введите количество метров ВОЛС (волоконно-оптической линии связи) или нажмите \"Пропустить\":",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode='HTML'
    )


async def _send_twisted_external_prompt(message) -> None:
    await message.reply_text(
        "📏 <b>Шаг 11/20: Метраж Внеш.витой пары</b>\n\n"
        "Введите количество метров внешней витой пары или нажмите \"Пропустить\":",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode='HTML'
    )


async def _send_twisted_internal_prompt(message) -> None:
    await message.reply_text(
        "📏 <b>Шаг 12/20: Метраж Внут.витой пары</b>\n\n"
        "Введите количество метров внутренней витой пары или нажмите \"Пропустить\":",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode='HTML'
    )


async def _send_account_number_prompt(message) -> None:
    await message.reply_text(
        "🔢 <b>Шаг 8/20: Номер лицевого счета абонента</b>\n\n"
        "Введите номер лицевого счета (только цифры, без ведущих нулей):",
        reply_markup=build_reply_keyboard(add_cancel=True),
        parse_mode='HTML'
    )


ACCOUNT_NUMBER_RE = re.compile(r"^[1-9]\d*$")


def _sync_twisted_total(context: ContextTypes.DEFAULT_TYPE) -> None:
    data = context.user_data.setdefault('connection_data', {})
    twisted_external = float(data.get('twisted_pair_external_meters', 0) or 0)
    twisted_internal = float(data.get('twisted_pair_internal_meters', 0) or 0)
    data['twisted_pair_meters'] = round(twisted_external + twisted_internal, 2)


async def enter_account_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод номера лицевого счета абонента."""
    text = (update.message.text or '').strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    if not ACCOUNT_NUMBER_RE.fullmatch(text):
        await update.message.reply_text(
            "⚠️ Введите корректный номер лицевого счета: только цифры, без ведущих нулей."
        )
        return ENTER_ACCOUNT_NUMBER

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['account_number'] = text
    await update.message.reply_text(
        f"🔢 <b>Шаг 8/20: Номер лицевого счета абонента</b>\n\n✅ Лицевой счет: {text}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await update.message.reply_text(
        "🔌 <b>Шаг 9/20: Номер порта</b>\n\n"
        "Введите номер порта или воспользуйтесь кнопкой \"Пропустить\":",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode='HTML'
    )
    return ENTER_PORT


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
                "🔌 <b>Шаг 9/20: Номер порта</b>\n\n⏭️ Порт пропущен.",
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
            "🔌 <b>Шаг 9/20: Номер порта</b>\n\n⏭️ Порт пропущен.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        await _send_fiber_prompt(update.message)
        return ENTER_FIBER

    context.user_data['connection_data']['port'] = port
    await update.message.reply_text(
        f"🔌 <b>Шаг 9/20: Номер порта</b>\n\n✅ Порт: {port}",
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
    if text == SKIP_TEXT:
        context.user_data.setdefault('connection_data', {})
        context.user_data['connection_data']['fiber_meters'] = 0.0
        await update.message.reply_text(
            "📏 <b>Шаг 10/20: Метраж ВОЛС</b>\n\n⏭️ Пропущено.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        await _send_twisted_external_prompt(update.message)
        return ENTER_TWISTED
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
        f"📏 <b>Шаг 10/20: Метраж ВОЛС</b>\n\n✅ ВОЛС: {fiber} м",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await _send_twisted_external_prompt(update.message)
    return ENTER_TWISTED


async def enter_twisted(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод метража внешней витой пары."""
    text = (update.message.text or '').strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    if text == SKIP_TEXT:
        context.user_data.setdefault('connection_data', {})
        context.user_data['connection_data']['twisted_pair_external_meters'] = 0.0
        _sync_twisted_total(context)
        await update.message.reply_text(
            "📏 <b>Шаг 11/20: Метраж Внеш.витой пары</b>\n\n⏭️ Пропущено.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        await _send_twisted_internal_prompt(update.message)
        return ENTER_TWISTED_INTERNAL

    try:
        twisted = float(text.replace(',', '.'))
        if twisted < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)")
        return ENTER_TWISTED

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['twisted_pair_external_meters'] = twisted
    _sync_twisted_total(context)
    await update.message.reply_text(
        f"📏 <b>Шаг 11/20: Метраж Внеш.витой пары</b>\n\n✅ Внешняя витая пара: {twisted} м",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    await _send_twisted_internal_prompt(update.message)
    return ENTER_TWISTED_INTERNAL


async def enter_twisted_internal(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод метража внутренней витой пары."""
    text = (update.message.text or '').strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    if text == SKIP_TEXT:
        context.user_data.setdefault('connection_data', {})
        context.user_data['connection_data']['twisted_pair_internal_meters'] = 0.0
        _sync_twisted_total(context)
        await update.message.reply_text(
            "📏 <b>Шаг 12/20: Метраж Внут.витой пары</b>\n\n⏭️ Пропущено.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        from handlers.connection.steps import start_snr_step
        return await start_snr_step(update, context, db)

    try:
        twisted = float(text.replace(',', '.'))
        if twisted < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)")
        return ENTER_TWISTED_INTERNAL

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['twisted_pair_internal_meters'] = twisted
    _sync_twisted_total(context)
    await update.message.reply_text(
        f"📏 <b>Шаг 12/20: Метраж Внут.витой пары</b>\n\n✅ Внутренняя витая пара: {twisted} м",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )
    from handlers.connection.steps import start_snr_step

    return await start_snr_step(update, context, db)
