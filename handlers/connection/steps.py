"""
Обработчики шагов создания подключения
"""
from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS,
    ENTER_PORT, ENTER_FIBER,
    ENTER_TWISTED, CONTRACT_SIGNED, TELEGRAM_BOT_CONFIRM, SELECT_SNR_BOX,
    SELECT_ONU_ACTION, ENTER_ONU_QUANTITY, SELECT_MEDIA_ACTION, ENTER_MEDIA_QUANTITY,
    ENTER_COMMENT, ENTER_SNR_QUANTITY_CONNECTION, CONNECTION_TYPES
)
from utils.keyboards import get_main_keyboard
from handlers.connection.constants import MAX_PHOTOS, PHOTO_REQUIREMENTS, CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.cancellation import cancel_connection
from handlers.connection.executors import start_employee_selection
from handlers.connection.devices import start_router_step, start_onu_step
from handlers.connection.comments import start_comment_step, enter_comment
from utils.helpers import run_in_thread
from handlers.connection.ui import (
    build_inline_keyboard,
    cancel_reply_keyboard,
    build_reply_keyboard,
    SKIP_TEXT,
    CANCEL_TEXT
)

# unify cancel text: use button text for comparisons
CANCEL_TEXT = CANCEL_TEXT or LEGACY_CANCEL_TEXT


# Вспомогательные шаги для перестановки последовательности
async def start_snr_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Шаг выбора SNR бокса (Шаг 10/16)"""
    snr_names = await run_in_thread(db.get_all_snr_box_names) or []
    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data'].setdefault('snr_box_model', '-')
    context.user_data['connection_data'].setdefault('snr_box_quantity', 0)

    chat_id = update.effective_chat.id if update.effective_chat else None

    if not snr_names:
        context.user_data['connection_data']['snr_box_model'] = '-'
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n\n⏭️ Пропущено.",
                parse_mode='HTML'
            )
        return await start_onu_step(update, context, db)

    keyboard = [
        [InlineKeyboardButton(f"🧰 {name}", callback_data=f"snr_box_{name}")]
        for name in snr_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data='snr_skip')])
    reply_markup = build_inline_keyboard(keyboard)

    text = (
        "🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n\n"
        "Выберите модель или пропустите шаг:"
    )
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    return SELECT_SNR_BOX


async def start_contract_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Шаг подтверждения договора (Шаг 13/16)"""
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("✅ Подтвердить", callback_data='contract_confirmed')],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='contract_skipped')],
    ])

    message_text = (
        "📄 <b>Шаг 13/16: Договор подписан, памятка передана</b>\n\n"
        "Подтвердите, что договор подписан и памятка передана абоненту:"
    )
    chat_id = update.effective_chat.id if update.effective_chat else None

    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    return CONTRACT_SIGNED


async def new_connection_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания нового подключения"""
    # Инициализация данных
    context.user_data['photos'] = []
    context.user_data['connection_data'] = {}
    
    # Создаем клавиатуру для выбора типа подключения
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("1️⃣ МКД", callback_data='conn_type_mkd')],
        [InlineKeyboardButton("2️⃣ ЧС", callback_data='conn_type_chs')],
        [InlineKeyboardButton("3️⃣ Юр / Гос", callback_data='conn_type_legal')]
    ])
    
    text = """
🏢 <b>Шаг 1/16: Тип подключения</b>

Выберите тип подключения:

1️⃣ МКД - многоквартирный дом
2️⃣ ЧС - частный сектор
3️⃣ Юр / Гос - юридическое лицо / государственная организация
"""
    
    # Проверяем, откуда пришел запрос
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return SELECT_CONNECTION_TYPE


async def select_connection_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение выбранного типа подключения"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем тип подключения из callback_data
    conn_type = query.data.split('_')[-1]
    context.user_data['connection_data']['connection_type'] = conn_type
    
    # Получаем читаемое название
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')]
    ])

    step_one_result = (
        "🏢 <b>Шаг 1/16: Тип подключения</b>\n\n"
        f"✅ Выбрано: <b>{type_name}</b>"
    )
    await query.edit_message_text(step_one_result, parse_mode='HTML')

    photos_prompt = (
        "📸 <b>Шаг 2/16: Загрузка фотографий</b>\n\n"
        f"Загрузите фотографии с места подключения (до {MAX_PHOTOS} штук).\n"
        "После загрузки фото нажмите \"Продолжить\".\n\n"
        f"{PHOTO_REQUIREMENTS}\n\n"
        "⚠️ <b>Внимание:</b> Загрузка фотографий обязательна!"
    )
    await query.message.reply_text(
        photos_prompt,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return UPLOAD_PHOTOS


async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Сохранение адреса и переход к выбору роутера"""
    address = update.message.text.strip()
    
    # Проверяем отмену
    if address == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    # Проверяем и инициализируем connection_data если нужно
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    context.user_data['connection_data']['address'] = address
    
    await update.message.reply_text(
        "📍 <b>Шаг 3/16: Адрес подключения</b>\n\n"
        f"✅ Адрес: {address}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='HTML'
    )

    return await start_router_step(update, context, db, address=address)


async def contract_signed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения договора и переход к подключению Телеграмм Бота"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем подтверждение договора
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    contract_confirmed = (query.data == 'contract_confirmed')
    context.user_data['connection_data']['contract_signed'] = contract_confirmed
    contract_status_text = (
        "📄 <b>Шаг 13/16: Договор подписан, памятка передана</b>\n\n"
        "✅ Подтверждено"
        if contract_confirmed
        else "📄 <b>Шаг 13/16: Договор подписан, памятка передана</b>\n\n"
             "⏭️ Пропущено"
    )
    
    # Переходим к новому шагу "Телеграмм Бот"
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("✅ Подтвердить", callback_data='telegram_bot_confirmed')],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='telegram_bot_skipped')]
    ])

    await query.edit_message_text(
        contract_status_text,
        parse_mode='HTML'
    )
    await query.message.reply_text(
        "🤖 <b>Шаг 14/16: Телеграмм Бот</b>\n\n"
        "Подтвердите, что абонентский Телеграмм Бот подключен:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return TELEGRAM_BOT_CONFIRM


async def telegram_bot_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка подтверждения подключения Телеграмм Бота"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем информацию о подключении Телеграмм Бота
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    if query.data == 'telegram_bot_confirmed':
        context.user_data['connection_data']['telegram_bot_connected'] = True
        status_text = "🤖 <b>Шаг 14/16: Телеграмм Бот</b>\n\n✅ Телеграмм Бот подключен"
    else:  # telegram_bot_skipped
        context.user_data['connection_data']['telegram_bot_connected'] = False
        status_text = "🤖 <b>Шаг 14/16: Телеграмм Бот</b>\n\n⏭️ Телеграмм Бот пропущен"

    await query.edit_message_text(
        status_text,
        parse_mode='HTML'
    )

    return await start_comment_step(update, context, db)
