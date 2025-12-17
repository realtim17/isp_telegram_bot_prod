"""Шаги выбора оборудования (роутеры, ONU, медиаконверторы, SFP)."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_ROUTER,
    ENTER_ROUTER_QUANTITY_CONNECTION,
    ROUTER_ACCESS,
    SELECT_SNR_BOX,
    ENTER_SNR_QUANTITY_CONNECTION,
    SELECT_ONU_ACTION,
    ENTER_ONU_QUANTITY,
    SELECT_MEDIA_ACTION,
    ENTER_MEDIA_QUANTITY,
    SELECT_SFP_ACTION,
    ENTER_SFP_QUANTITY,
)
from handlers.connection.constants import CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.ui import (
    build_inline_keyboard,
    cancel_reply_keyboard,
    CANCEL_TEXT as BUTTON_CANCEL_TEXT,
)
from handlers.connection.cancellation import cancel_connection
from utils.helpers import run_in_thread
from utils.keyboards import get_main_keyboard

CANCEL_TEXT_VARIANTS = tuple(
    text for text in (BUTTON_CANCEL_TEXT, LEGACY_CANCEL_TEXT) if text
)


async def start_router_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    address: str
) -> int:
    """Показать пользователю шаг выбора роутера (Шаг 4/16)."""
    router_names = await run_in_thread(db.get_all_router_names) or []

    keyboard = [
        [InlineKeyboardButton(f"📡 {router_name}", callback_data=f"select_router_{router_name}")]
        for router_name in router_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data='router_skip')])
    reply_markup = build_inline_keyboard(keyboard)

    if router_names:
        message_text = (
            "🌐 <b>Шаг 4/16: Модель роутера</b>\n\n"
            "Выберите роутер из списка или пропустите:"
        )
    else:
        message_text = (
            "🌐 <b>Шаг 4/16: Модель роутера</b>\n\n"
            "⚠️ В системе нет зарегистрированных роутеров.\n"
            "Вы можете пропустить этот шаг:"
        )

    message = update.effective_message
    if message:
        await message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    return SELECT_ROUTER


async def select_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора роутера или пропуска."""
    query = update.callback_query
    await query.answer()

    context.user_data.setdefault('connection_data', {})

    if query.data == 'router_skip':
        context.user_data['connection_data']['router_model'] = '-'
        context.user_data['connection_data']['router_quantity'] = 0

        reply_markup = build_inline_keyboard([
            [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')]
        ])

        await query.edit_message_text(
            "🌐 <b>Шаг 4/16: Модель роутера</b>\n\n⏭️ Пропущено.",
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n"
            "Подтвердите, что доступ на роутер открыт:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return ROUTER_ACCESS

    router_name = query.data.replace('select_router_', '')
    context.user_data['connection_data']['router_model'] = router_name

    await query.edit_message_text(
        "🌐 <b>Шаг 4/16: Модель роутера</b>\n\n"
        f"✅ Выбрано: <b>{router_name}</b>",
        parse_mode='HTML'
    )
    await query.message.reply_text(
        "📦 <b>Шаг 5/16: Количество роутеров</b>\n\n"
        "Введите количество роутеров (по умолчанию: 1):",
        reply_markup=cancel_reply_keyboard(),
        parse_mode='HTML'
    )
    return ENTER_ROUTER_QUANTITY_CONNECTION


async def enter_router_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода количества роутеров."""
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

    try:
        router_quantity = int(text)
        if router_quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число больше нуля (например: 1, 2, 3)"
        )
        return ENTER_ROUTER_QUANTITY_CONNECTION

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['router_quantity'] = router_quantity

    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')]
    ])

    await update.message.reply_text(
        "✅ Количество принято.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "📦 <b>Шаг 5/16: Количество роутеров</b>\n"
        f"✅ Количество: {router_quantity}",
        parse_mode='HTML'
    )
    await update.message.reply_text(
        "🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n"
        "Подтвердите, что доступ на роутер открыт:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return ROUTER_ACCESS


async def select_snr_box(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_connection":
        return await cancel_connection(update, context)

    context.user_data.setdefault("connection_data", {})
    if query.data == "snr_skip":
        context.user_data["connection_data"]["snr_box_model"] = "-"
        context.user_data["connection_data"]["snr_box_quantity"] = 0
        await query.edit_message_text(
            "🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n\n⏭️ Пропущено.",
            parse_mode="HTML"
        )
        return await start_onu_step(update, context, db)

    box_name = query.data.replace("snr_box_", "", 1)
    context.user_data["connection_data"]["snr_box_model"] = box_name
    await query.edit_message_text(
        "🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n\n"
        f"Выбрано: <b>{box_name}</b>\n"
        "🔢 Укажите количество (шт.):",
        parse_mode="HTML",
    )
    return ENTER_SNR_QUANTITY_CONNECTION


async def enter_snr_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_SNR_QUANTITY_CONNECTION

    context.user_data.setdefault("connection_data", {})
    context.user_data["connection_data"]["snr_box_quantity"] = quantity
    snr_model = context.user_data["connection_data"]["snr_box_model"]

    await update.message.reply_text(
        "✅ Количество принято.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n"
        f"✅ Модель: <b>{snr_model}</b>\n"
        f"✅ Количество: {quantity} шт.",
        parse_mode="HTML"
    )

    return await start_onu_step(update, context, db)


async def start_onu_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    onu_names = await run_in_thread(db.get_all_onu_names) or []
    context.user_data.setdefault("connection_data", {})
    context.user_data["connection_data"].setdefault("onu_model", "-")
    context.user_data["connection_data"].setdefault("onu_quantity", 0)

    if not onu_names:
        context.user_data["connection_data"]["onu_model"] = "-"
        context.user_data["connection_data"]["onu_quantity"] = 0
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n\n⏭️ Пропущено.",
                parse_mode="HTML"
            )
        return await start_media_step(update, context, db)

    keyboard = [
        [InlineKeyboardButton(f"🔌 {name}", callback_data=f"conn_onu_{name}")]
        for name in onu_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="conn_onu_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_connection")])

    text = (
        "🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n\n"
        "Выберите модель или пропустите шаг:"
    )
    markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    return SELECT_ONU_ACTION


async def select_onu_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "conn_onu_skip":
        context.user_data["connection_data"]["onu_model"] = "-"
        context.user_data["connection_data"]["onu_quantity"] = 0
        await query.edit_message_text(
            "🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n\n⏭️ Пропущено.",
            parse_mode="HTML"
        )
        return await start_media_step(update, context, db)

    if query.data == "cancel_connection":
        return await cancel_connection(update, context)

    if query.data.startswith("conn_onu_"):
        model = query.data.replace("conn_onu_", "", 1)
        context.user_data["connection_data"]["onu_model"] = model
        text = (
            "🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n\n"
            f"Выбрано: <b>{model}</b>\n"
            "🔢 Укажите количество (шт.):"
        )
        await query.edit_message_text(text, parse_mode="HTML")
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=cancel_reply_keyboard()
        )
        return ENTER_ONU_QUANTITY

    return SELECT_ONU_ACTION


async def enter_onu_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_ONU_QUANTITY

    context.user_data["connection_data"]["onu_quantity"] = quantity
    onu_model = context.user_data["connection_data"]["onu_model"]

    await update.message.reply_text(
        "✅ Количество принято.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n"
        f"✅ Модель: <b>{onu_model}</b>\n"
        f"✅ Количество: {quantity} шт.",
        parse_mode="HTML"
    )

    return await start_media_step(update, context, db)


async def start_media_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    media_names = await run_in_thread(db.get_all_media_converter_names) or []
    context.user_data.setdefault("connection_data", {})
    context.user_data["connection_data"].setdefault("media_converter_model", "-")
    context.user_data["connection_data"].setdefault("media_converter_quantity", 0)

    if not media_names:
        context.user_data["connection_data"]["media_converter_model"] = "-"
        context.user_data["connection_data"]["media_converter_quantity"] = 0
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n⏭️ Пропущено.",
                parse_mode="HTML"
            )
        return await start_sfp_step(update, context, db)

    keyboard = [
        [InlineKeyboardButton(f"🔄 {name}", callback_data=f"conn_media_{name}")]
        for name in media_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="conn_media_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_connection")])

    text = (
        "🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n"
        "Выберите модель или пропустите шаг:"
    )
    markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    return SELECT_MEDIA_ACTION


async def select_media_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "conn_media_skip":
        context.user_data["connection_data"]["media_converter_model"] = "-"
        context.user_data["connection_data"]["media_converter_quantity"] = 0
        await query.edit_message_text(
            "🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n⏭️ Пропущено.",
            parse_mode="HTML"
        )
        return await start_sfp_step(update, context, db)

    if query.data == "cancel_connection":
        return await cancel_connection(update, context)

    if query.data.startswith("conn_media_"):
        model = query.data.replace("conn_media_", "", 1)
        context.user_data["connection_data"]["media_converter_model"] = model
        text = (
            "🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n"
            f"Выбрано: <b>{model}</b>\n"
            "🔢 Укажите количество (шт.):"
        )
        await query.edit_message_text(text, parse_mode="HTML")
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=cancel_reply_keyboard()
        )
        return ENTER_MEDIA_QUANTITY

    return SELECT_MEDIA_ACTION


async def enter_media_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_MEDIA_QUANTITY

    context.user_data["connection_data"]["media_converter_quantity"] = quantity
    media_model = context.user_data["connection_data"]["media_converter_model"]

    await update.message.reply_text(
        "✅ Количество принято.",
        reply_markup=ReplyKeyboardRemove()
    )
    await update.message.reply_text(
        "🔄 <b>Шаг 12/16: Медиаконверторы</b>\n"
        f"✅ Модель: <b>{media_model}</b>\n"
        f"✅ Количество: {quantity} шт.",
        parse_mode="HTML"
    )

    return await start_sfp_step(update, context, db)


async def start_sfp_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    module_names = await run_in_thread(db.get_all_sfp_module_names) or []
    context.user_data.setdefault("connection_data", {})
    context.user_data["connection_data"].setdefault("sfp_module_model", "-")
    context.user_data["connection_data"].setdefault("sfp_module_quantity", 0)

    if not module_names:
        context.user_data["connection_data"]["sfp_module_model"] = "-"
        context.user_data["connection_data"]["sfp_module_quantity"] = 0
        from handlers.connection.steps import start_contract_step
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🧿 <b>Шаг 13/16: SFP модули</b>\n\n⏭️ Пропущено.",
                parse_mode="HTML"
            )
        return await start_contract_step(update, context)

    keyboard = [
        [InlineKeyboardButton(f"🧿 {name}", callback_data=f"conn_sfp_{name}")]
        for name in module_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="conn_sfp_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_connection")])

    text = (
        "🧿 <b>Шаг 13/16: SFP модули</b>\n\n"
        "Выберите модель или пропустите шаг:"
    )
    markup = InlineKeyboardMarkup(keyboard)
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    return SELECT_SFP_ACTION


async def select_sfp_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "conn_sfp_skip":
        context.user_data["connection_data"]["sfp_module_model"] = "-"
        context.user_data["connection_data"]["sfp_module_quantity"] = 0
        from handlers.connection.steps import start_contract_step
        await query.edit_message_text(
            "🧿 <b>Шаг 13/16: SFP модули</b>\n\n⏭️ Пропущено.",
            parse_mode="HTML"
        )
        return await start_contract_step(update, context)

    if query.data == "cancel_connection":
        return await cancel_connection(update, context)

    if query.data.startswith("conn_sfp_"):
        model = query.data.replace("conn_sfp_", "", 1)
        context.user_data["connection_data"]["sfp_module_model"] = model
        text = (
            "🧿 <b>Шаг 13/16: SFP модули</b>\n\n"
            f"Выбрано: <b>{model}</b>\n"
            "🔢 Укажите количество (шт.):"
        )
        await query.edit_message_text(text, parse_mode="HTML")
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=cancel_reply_keyboard()
        )
        return ENTER_SFP_QUANTITY

    return SELECT_SFP_ACTION


async def enter_sfp_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\nВсе введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_SFP_QUANTITY

    context.user_data["connection_data"]["sfp_module_quantity"] = quantity
    module_model = context.user_data["connection_data"].get("sfp_module_model", "-")

    await update.message.reply_text(
        "🧿 <b>Шаг 13/16: SFP модули</b>\n"
        f"✅ Модель: <b>{module_model}</b>\n"
        f"✅ Количество: {quantity} шт.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

    from handlers.connection.steps import start_contract_step

    return await start_contract_step(update, context)
