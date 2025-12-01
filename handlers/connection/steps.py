"""
Обработчики шагов создания подключения
"""
from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS, SELECT_ROUTER,
    ENTER_ROUTER_QUANTITY_CONNECTION, ROUTER_ACCESS, ENTER_PORT, ENTER_FIBER,
    ENTER_TWISTED, CONTRACT_SIGNED, TELEGRAM_BOT_CONFIRM, SELECT_SNR_BOX,
    SELECT_ONU_ACTION, ENTER_ONU_QUANTITY, SELECT_MEDIA_ACTION, ENTER_MEDIA_QUANTITY,
    ENTER_COMMENT, ENTER_SNR_QUANTITY_CONNECTION, CONNECTION_TYPES
)
from utils.keyboards import get_main_keyboard
from handlers.connection.constants import MAX_PHOTOS, PHOTO_REQUIREMENTS, CANCEL_TEXT as LEGACY_CANCEL_TEXT
from handlers.connection.cancellation import cancel_connection
from handlers.connection.employees import start_employee_selection
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
async def start_snr_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db, pre_text: str = "") -> int:
    """Шаг выбора SNR бокса (Шаг 10/16)"""
    snr_names = await run_in_thread(db.get_all_snr_box_names) or []
    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data'].setdefault('snr_box_model', '-')
    context.user_data['connection_data'].setdefault('snr_box_quantity', 0)

    if not snr_names:
        context.user_data['connection_data']['snr_box_model'] = '-'
        return await start_onu_step(update, context, db, pre_text=pre_text + "\n🧰 SNR бокс: <b>Пропущен</b>")

    keyboard = [
        [InlineKeyboardButton(f"🧰 {name}", callback_data=f"snr_box_{name}")]
        for name in snr_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data='snr_skip')])
    reply_markup = build_inline_keyboard(keyboard)

    chat_id = update.effective_chat.id if update.effective_chat else None
    text = (
        f"{pre_text}\n\n"
        f"🧰 <b>Шаг 10/16: SNR Оптический бокс</b>\n\n"
        f"Выберите модель или пропустите шаг:"
    )
    # Отправляем отдельным сообщением, чтобы исключить проблемы с edit_message_text
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_SNR_BOX


async def start_contract_step(update: Update, context: ContextTypes.DEFAULT_TYPE, pre_text: str = "") -> int:
    """Шаг подтверждения договора (Шаг 13/16)"""
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("✅ Подтверждаю", callback_data='contract_confirmed')],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='contract_skipped')],
    ])

    text = []
    if pre_text:
        text.append(pre_text)
    text.append("📄 <b>Шаг 13/16: Договор подписан</b>\n\nПодтвердите, что договор подписан:")
    message_text = "\n\n".join(text)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            message_text,
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
    
    text = f"""
✅ Тип подключения: <b>{type_name}</b>

📸 <b>Шаг 2/16: Загрузка фотографий</b>

Загрузите фотографии с места подключения (до {MAX_PHOTOS} штук).
После загрузки фото нажмите "Продолжить".

{PHOTO_REQUIREMENTS}

⚠️ <b>Внимание:</b> Загрузка фотографий обязательна!
"""
    
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')]
    ])
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return UPLOAD_PHOTOS


async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка загружаемых фотографий"""
    if update.message.photo:
        photos = context.user_data.get('photos', [])
        
        if len(photos) >= MAX_PHOTOS:
            await update.message.reply_text(f"⚠️ Достигнут лимит в {MAX_PHOTOS} фотографий.")
            return UPLOAD_PHOTOS
        
        # Сохраняем file_id самого большого размера фото
        photo_file_id = update.message.photo[-1].file_id
        photos.append(photo_file_id)
        context.user_data['photos'] = photos
        
        reply_markup = build_inline_keyboard([
            [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')]
        ])
        
        # Если это первое фото - отправляем новое сообщение и сохраняем его ID
        if len(photos) == 1:
            sent_message = await update.message.reply_text(
                f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                reply_markup=reply_markup
            )
            context.user_data['upload_message_id'] = sent_message.message_id
        else:
            # Для последующих фото - редактируем существующее сообщение
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data.get('upload_message_id'),
                    text=f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                         f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                    reply_markup=reply_markup
                )
            except Exception:
                # Если не удалось отредактировать, отправляем новое
                sent_message = await update.message.reply_text(
                    f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                    f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                    reply_markup=reply_markup
                )
                context.user_data['upload_message_id'] = sent_message.message_id
        
        return UPLOAD_PHOTOS
    
    return UPLOAD_PHOTOS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос адреса подключения"""
    query = update.callback_query
    await query.answer()
    
    photos_count = len(context.user_data.get('photos', []))
    
    # Проверяем, что загружено хотя бы одно фото
    if photos_count == 0:
        await query.edit_message_text(
            "⚠️ <b>Ошибка:</b> Необходимо загрузить хотя бы одно фото!\n\n"
            "📸 Загрузите фотографии с места подключения.",
            parse_mode='HTML'
        )
        return UPLOAD_PHOTOS
    
    # Создаём клавиатуру с кнопкой отмены
    reply_markup = cancel_reply_keyboard()
    
    await query.edit_message_text(
        f"✅ Загружено фото: {photos_count}\n\n"
        f"📍 <b>Шаг 3/16: Адрес подключения</b>\n\n"
        f"Введите адрес подключения абонента:",
        parse_mode='HTML'
    )
    
    # Отправляем сообщение с клавиатурой отмены
    await query.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=reply_markup
    )
    
    return ENTER_ADDRESS


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
    
    # Получаем список роутеров из БД
    router_names = await run_in_thread(db.get_all_router_names) or []
    
    # Создаём клавиатуру с роутерами
    keyboard = []
    
    if router_names:
        for router_name in router_names:
            keyboard.append([InlineKeyboardButton(
                f"📡 {router_name}",
                callback_data=f"select_router_{router_name}"
            )])
    
    # Добавляем кнопку "Пропустить"
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data='router_skip')])
    reply_markup = build_inline_keyboard(keyboard)
    
    # Убираем reply-клавиатуру
    await update.message.reply_text(
        "✅ Адрес сохранен.",
        reply_markup=ReplyKeyboardRemove()
    )

    # Показываем inline-клавиатуру
    if router_names:
        message_text = f"✅ Адрес: {address}\n\n🌐 <b>Шаг 4/16: Модель роутера</b>\n\nВыберите роутер из списка или пропустите:"
    else:
        message_text = f"✅ Адрес: {address}\n\n🌐 <b>Шаг 4/16: Модель роутера</b>\n\n⚠️ В системе нет зарегистрированных роутеров.\nВы можете пропустить этот шаг:"
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_ROUTER


async def select_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора роутера или пропуска"""
    query = update.callback_query
    await query.answer()
    
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    # Обработка пропуска
    if query.data == 'router_skip':
        context.user_data['connection_data']['router_model'] = '-'
        context.user_data['connection_data']['router_quantity'] = 0
        
        # Сразу переходим к шагу "Доступ на роутер"
        reply_markup = build_inline_keyboard([
            [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')]
        ])
        
        await query.edit_message_text(
            f"⏭️ Роутер: пропущено\n\n"
            f"🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n"
            f"Подтвердите, что доступ на роутер открыт:",
            parse_mode='HTML'
        )
        
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return ROUTER_ACCESS
    
    # Выбран роутер из списка
    router_name = query.data.replace('select_router_', '')
    context.user_data['connection_data']['router_model'] = router_name
    
    # Добавляем клавиатуру отмены для ввода количества роутеров
    reply_markup_kb = cancel_reply_keyboard()
    
    await query.edit_message_text(
        f"✅ Роутер: {router_name}\n\n"
        f"📦 <b>Шаг 5/16: Количество роутеров</b>\n\n"
        f"Введите количество роутеров (по умолчанию: 1):",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=reply_markup_kb
    )
    
    return ENTER_ROUTER_QUANTITY_CONNECTION


async def enter_router_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода количества роутеров"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == CANCEL_TEXT:
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
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['router_quantity'] = router_quantity
        
        # Переход к новому шагу "Доступ на роутер"
        reply_markup = build_inline_keyboard([
            [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')]
        ])

        await update.message.reply_text(
            "✅ Количество принято.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await update.message.reply_text(
            f"✅ Количество роутеров: {router_quantity}\n\n"
            f"🔐 <b>Шаг 6/16: Доступ на роутер</b>\n\n"
            f"Подтвердите, что доступ на роутер открыт:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return ROUTER_ACCESS
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число больше нуля (например: 1, 2, 3)"
        )
        return ENTER_ROUTER_QUANTITY_CONNECTION


async def router_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения доступа на роутер"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем информацию о доступе на роутер
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    if query.data == 'router_access_confirmed':
        context.user_data['connection_data']['router_access'] = True
        status_text = "✅ Доступ получен"
    else:  # router_access_skipped
        context.user_data['connection_data']['router_access'] = False
        status_text = "⏭️ Пропущено"
    
    await query.edit_message_text(
        f"{status_text}\n\n"
        f"🔌 <b>Шаг 7/16: Номер порта</b>\n\n"
        f"Введите номер порта или пропустите:",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        "Введите номер порта текстом или воспользуйтесь кнопками ниже:",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]])
    )
    
    return ENTER_PORT


async def _prompt_fiber_input(message, status_text: str):
    """Вывести подсказку для ввода метража ВОЛС"""
    await message.reply_text(
        f"{status_text}\n\n"
        f"📏 <b>Шаг 8/16: Метраж ВОЛС</b>\n\n"
        f"Введите количество метров ВОЛС (волоконно-оптической линии связи):",
        reply_markup=cancel_reply_keyboard(),
        parse_mode='HTML'
    )


async def enter_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение порта и запрос метража ВОЛС"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'cancel_connection':
            return await cancel_connection(update, context)
        
        if query.data == 'port_skip':
            if 'connection_data' not in context.user_data:
                context.user_data['connection_data'] = {}
            context.user_data['connection_data']['port'] = '-'
            await _prompt_fiber_input(query.message, "⏭️ Порт: пропущено")
            return ENTER_FIBER
        return ENTER_PORT
    
    port = (update.message.text or "").strip()
    
    if port == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    if port == SKIP_TEXT:
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        context.user_data['connection_data']['port'] = '-'
        await _prompt_fiber_input(update.message, "⏭️ Порт: пропущено")
        return ENTER_FIBER
    
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    context.user_data['connection_data']['port'] = port
    
    await _prompt_fiber_input(update.message, f"✅ Порт: {port}")
    return ENTER_FIBER


async def enter_fiber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение метража ВОЛС и запрос метража витой пары"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        fiber_meters = float(text.replace(',', '.'))
        if fiber_meters < 0:
            raise ValueError
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['fiber_meters'] = fiber_meters
        
        await update.message.reply_text(
            f"✅ ВОЛС: {fiber_meters} м\n\n"
            f"📏 <b>Шаг 9/16: Метраж витой пары</b>\n\n"
            f"Введите количество метров витой пары:",
            parse_mode='HTML'
        )
        
        return ENTER_TWISTED
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_FIBER


async def enter_twisted(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Сохранение метража витой пары и переход к подтверждению договора"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        twisted_meters = float(text.replace(',', '.'))
        if twisted_meters < 0:
            raise ValueError
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['twisted_pair_meters'] = twisted_meters

        await update.message.reply_text(
            f"✅ Витая пара: {twisted_meters} м\n\n"
            f"🧰 Переходим к выбору SNR бокса.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )

        # Переходим к шагу SNR (Шаг 10/16)
        return await start_snr_step(update, context, db)
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED


async def contract_signed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения договора и переход к подключению Телеграмм Бота"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем подтверждение договора
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    context.user_data['connection_data']['contract_signed'] = (query.data == 'contract_confirmed')
    
    # Переходим к новому шагу "Телеграмм Бот"
    reply_markup = build_inline_keyboard([
        [InlineKeyboardButton("✅ Подтвердить", callback_data='telegram_bot_confirmed')],
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='telegram_bot_skipped')]
    ])
    
    await query.edit_message_text(
        f"✅ Договор подписан\n\n"
        f"🤖 <b>Шаг 14/16: Телеграмм Бот</b>\n\n"
        f"Подтвердите, что абонентский Телеграмм Бот подключен:",
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
        status_text = "✅ Телеграмм Бот подключен"
    else:  # telegram_bot_skipped
        context.user_data['connection_data']['telegram_bot_connected'] = False
        status_text = "⏭️ Пропущено"

    return await start_comment_step(update, context, db, pre_text=status_text)


async def select_snr_box(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора SNR бокса"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    context.user_data.setdefault('connection_data', {})
    if query.data == 'snr_skip':
        context.user_data['connection_data']['snr_box_model'] = '-'
        context.user_data['connection_data']['snr_box_quantity'] = 0
        snr_status = "⏭️ SNR бокс: <b>Пропущен</b>"
        return await start_onu_step(update, context, db, pre_text=snr_status)

    box_name = query.data.replace('snr_box_', '', 1)
    context.user_data['connection_data']['snr_box_model'] = box_name
    await query.edit_message_text(
        f"🧰 SNR бокс: {box_name}\n\n"
        f"🔢 Укажите количество (шт.):",
        parse_mode='HTML'
    )
    return ENTER_SNR_QUANTITY_CONNECTION


async def enter_snr_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества SNR боксов"""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_SNR_QUANTITY_CONNECTION

    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data']['snr_box_quantity'] = quantity
    snr_status = f"🧰 SNR бокс: <b>{context.user_data['connection_data']['snr_box_model']}</b> ({quantity} шт.)"
    return await start_onu_step(update, context, db, pre_text=snr_status)


async def start_onu_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db, pre_text: str = "") -> int:
    """Шаг выбора ONU"""
    onu_names = await run_in_thread(db.get_all_onu_names) or []
    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data'].setdefault('onu_model', '-')
    context.user_data['connection_data'].setdefault('onu_quantity', 0)
    
    if not onu_names:
        context.user_data['connection_data']['onu_model'] = '-'
        context.user_data['connection_data']['onu_quantity'] = 0
        return await start_media_step(update, context, db, pre_text=pre_text + "\n🔌 ONU: <b>Пропущено</b>")
    
    keyboard = [
        [InlineKeyboardButton(f"🔌 {name}", callback_data=f"conn_onu_{name}")]
        for name in onu_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="conn_onu_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_connection")])

    text = (
        f"{pre_text}\n\n"
        f"🔌 <b>Шаг 11/16: ONU Абонентский терминал</b>\n\n"
        f"Выберите модель или пропустите шаг:"
    )
    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
    return SELECT_ONU_ACTION


async def select_onu_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор модели ONU"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "conn_onu_skip":
        context.user_data['connection_data']['onu_model'] = '-'
        context.user_data['connection_data']['onu_quantity'] = 0
        return await start_media_step(update, context, db, pre_text="🔌 ONU: <b>Пропущено</b>")
    
    if query.data.startswith("conn_onu_"):
        model = query.data.replace("conn_onu_", "", 1)
        context.user_data['connection_data']['onu_model'] = model
        text = (
            f"🔌 ONU: {model}\n\n"
            f"🔢 Укажите количество (шт.):"
        )
        if query:
            await query.edit_message_text(text, parse_mode='HTML')
            await query.message.reply_text(
                "Для отмены нажмите кнопку ниже:",
                reply_markup=cancel_reply_keyboard()
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=cancel_reply_keyboard(),
                parse_mode='HTML'
            )
        return ENTER_ONU_QUANTITY
    
    return SELECT_ONU_ACTION


async def enter_onu_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества ONU"""
    text = (update.message.text or "").strip()
    if text == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_ONU_QUANTITY
    
    context.user_data['connection_data']['onu_quantity'] = quantity
    status = f"🔌 ONU: <b>{context.user_data['connection_data']['onu_model']}</b> ({quantity} шт.)"
    return await start_media_step(update, context, db, pre_text=status)


async def start_media_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db, pre_text: str = "") -> int:
    """Шаг выбора медиаконверторов"""
    media_names = await run_in_thread(db.get_all_media_converter_names) if db else []
    media_names = media_names or []
    context.user_data.setdefault('connection_data', {})
    context.user_data['connection_data'].setdefault('media_converter_model', '-')
    context.user_data['connection_data'].setdefault('media_converter_quantity', 0)
    
    if not media_names:
        context.user_data['connection_data']['media_converter_model'] = '-'
        context.user_data['connection_data']['media_converter_quantity'] = 0
        return await start_contract_step(update, context, pre_text=pre_text + "\n🔄 Медиаконвертор: <b>Пропущен</b>")
    
    keyboard = [
        [InlineKeyboardButton(f"🔄 {name}", callback_data=f"conn_media_{name}")]
        for name in media_names
    ]
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data="conn_media_skip")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_connection")])
    
    if update.callback_query:
        target_msg = update.callback_query
        await target_msg.edit_message_text(
            f"{pre_text}\n\n"
            f"🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n"
            f"Выберите модель или пропустите шаг:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            f"{pre_text}\n\n"
            f"🔄 <b>Шаг 12/16: Медиаконверторы</b>\n\n"
            f"Выберите модель или пропустите шаг:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    return SELECT_MEDIA_ACTION


async def select_media_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор модели медиаконвертора"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "conn_media_skip":
        context.user_data['connection_data']['media_converter_model'] = '-'
        context.user_data['connection_data']['media_converter_quantity'] = 0
        pre = "🔄 Медиаконвертор: <b>Пропущен</b>"
        return await start_contract_step(update, context, pre_text=pre)
    
    if query.data.startswith("conn_media_"):
        model = query.data.replace("conn_media_", "", 1)
        context.user_data['connection_data']['media_converter_model'] = model
        text = (
            f"🔄 Медиаконвертор: {model}\n\n"
            f"🔢 Укажите количество (шт.):"
        )
        if update.callback_query:
            await query.edit_message_text(text, parse_mode='HTML')
            await query.message.reply_text(
                "Для отмены нажмите кнопку ниже:",
                reply_markup=cancel_reply_keyboard()
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=cancel_reply_keyboard(),
                parse_mode='HTML'
            )
        return ENTER_MEDIA_QUANTITY
    
    return SELECT_MEDIA_ACTION


async def enter_media_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества медиаконверторов"""
    text = (update.message.text or "").strip()
    if text == CANCEL_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return ENTER_MEDIA_QUANTITY
    
    context.user_data['connection_data']['media_converter_quantity'] = quantity
    pre = (
        f"🔌 ONU: <b>{context.user_data['connection_data'].get('onu_model', '-')}</b> "
        f"({context.user_data['connection_data'].get('onu_quantity', 0)} шт.)\n"
        f"🔄 Медиаконвертор: <b>{context.user_data['connection_data'].get('media_converter_model', '-')}</b> "
        f"({quantity} шт.)"
    )
    return await start_contract_step(update, context, pre_text=pre)


async def start_comment_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db, pre_text: str = "") -> int:
    """Запрос комментария перед выбором исполнителей"""
    context.user_data.setdefault('connection_data', {})
    context.user_data['comment_pre_text'] = pre_text

    parts = []
    if pre_text:
        parts.append(pre_text)
    parts.append(
        "💬 <b>Шаг 15/16: Комментарий</b>\n\n"
        "Оставьте комментарий по подключению (сложности, нюансы, потраченные материалы и т.д.).\n"
        "Если комментарий не нужен, нажмите \"Пропустить\"."
    )
    message_text = "\n\n".join(parts)

    reply_markup = build_reply_keyboard([[SKIP_TEXT]], add_cancel=True)

    if update.callback_query:
        query = update.callback_query
        await query.edit_message_text(
            message_text,
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "Введите комментарий или нажмите кнопку ниже:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    return ENTER_COMMENT


async def enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Сохранить комментарий и перейти к выбору исполнителей"""
    text = (update.message.text or "").strip()

    if text == CANCEL_TEXT:
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

    confirm_text = "✅ Комментарий сохранен."
    if text == SKIP_TEXT or not text:
        confirm_text = "⏭️ Комментарий пропущен."
    await update.message.reply_text(confirm_text, reply_markup=ReplyKeyboardRemove())

    pre_text = context.user_data.pop('comment_pre_text', None)
    return await start_employee_selection(update, context, db, pre_text=pre_text)
