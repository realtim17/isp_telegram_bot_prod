"""Шаги сценария «Магистральная линия» в рамках общего ConversationHandler."""
from typing import List

from telegram import Update, InlineKeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    MAG_UPLOAD_PHOTOS,
    MAG_ENTER_ADDRESS,
    MAG_ENTER_FIBER,
    MAG_ENTER_HOOKS,
    MAG_ENTER_ORK,
    MAG_ENTER_MUFTS,
    MAG_SELECT_SFP,
    MAG_ENTER_SFP_QTY,
    MAG_COMMENT,
    MAG_SELECT_EMPLOYEES,
)
from handlers.connection.constants import (
    MAX_PHOTOS,
    PHOTO_REQUIREMENTS,
    CANCEL_TEXT as CANCEL_MESSAGE,
)
from handlers.connection.executors import start_employee_selection
from handlers.connection.ui import (
    CANCEL_TEXT as BUTTON_CANCEL_TEXT,
    SKIP_TEXT,
    build_inline_keyboard,
    build_reply_keyboard,
    cancel_reply_keyboard,
)
from handlers.connection.cancellation import cancel_connection
from handlers.connection.validation import check_materials_and_proceed
from handlers.connection.confirmation import show_confirmation
from utils.helpers import run_in_thread
from utils.keyboards import get_main_keyboard


CANCEL_TEXT_VARIANTS = tuple(
    text for text in (BUTTON_CANCEL_TEXT,) if text
)


def _get_connection_data(context: ContextTypes.DEFAULT_TYPE) -> dict:
    data = context.user_data.setdefault("connection_data", {})
    defaults = {
        "connection_type": "magistral",
        "router_model": "-",
        "router_quantity": 0,
        "snr_box_model": "-",
        "snr_box_quantity": 0,
        "fiber_meters": 0.0,
        "twisted_pair_meters": 0.0,
        "hooks_quantity": 0.0,
        "ork_quantity": 0.0,
        "mufta_quantity": 0.0,
        "port": "-",
        "router_access": False,
        "contract_signed": False,
        "telegram_bot_connected": False,
        "onu_model": "-",
        "onu_quantity": 0,
        "media_converter_model": "-",
        "media_converter_quantity": 0,
        "sfp_module_model": "-",
        "sfp_module_quantity": 0,
        "comment": "-",
    }
    for key, value in defaults.items():
        data.setdefault(key, value)
    return data


async def _cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    message = update.effective_message
    if message:
        await message.reply_text(
            CANCEL_MESSAGE,
            reply_markup=get_main_keyboard(),
            parse_mode="HTML",
        )
    return ConversationHandler.END


async def start_magistral_from_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Переводит пользователя на сценарий магистрали после выбора типа."""
    query = update.callback_query
    await query.answer()

    context.user_data.setdefault("photos", [])
    data = _get_connection_data(context)
    data["connection_type"] = "magistral"

    step_result = (
        "🏢 <b>Шаг 1/11: Тип подключения</b>\n\n"
        "✅ Выбрано: <b>Магистральная линия</b>"
    )
    await query.edit_message_text(step_result, parse_mode="HTML")

    instructions = (
        "📸 <b>Шаг 2/11: Фото с объекта</b>\n\n"
        f"Загрузите фото (до {MAX_PHOTOS} штук).\n"
        "После загрузки нажмите «Продолжить».\n\n"
        f"{PHOTO_REQUIREMENTS}"
    )
    reply_markup = build_inline_keyboard(
        [[InlineKeyboardButton("➡️ Продолжить", callback_data="mag_continue_from_photos")]]
    )
    await query.message.reply_text(
        instructions,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )

    return MAG_UPLOAD_PHOTOS


async def mag_upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка фотографий магистральной линии."""
    if not update.message or not update.message.photo:
        return MAG_UPLOAD_PHOTOS

    photos: List[str] = context.user_data.setdefault("photos", [])
    if len(photos) >= MAX_PHOTOS:
        await update.message.reply_text(
            f"⚠️ Достигнут лимит в {MAX_PHOTOS} фотографий.", parse_mode="HTML"
        )
        return MAG_UPLOAD_PHOTOS

    photo_id = update.message.photo[-1].file_id
    photos.append(photo_id)
    context.user_data["photos"] = photos

    reply_markup = build_inline_keyboard(
        [[InlineKeyboardButton("➡️ Продолжить", callback_data="mag_continue_from_photos")]]
    )

    status_text = (
        "📸 <b>Шаг 2/11: Фото с объекта</b>\n\n"
        f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
        "Можете загрузить дополнительные фото или нажмите «Продолжить»."
    )

    message_id = context.user_data.get("mag_upload_message_id")
    chat_id = update.effective_chat.id if update.effective_chat else None
    if message_id and chat_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=status_text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return MAG_UPLOAD_PHOTOS
        except Exception:
            pass

    sent = await update.message.reply_text(
        status_text,
        reply_markup=reply_markup,
        parse_mode="HTML",
    )
    context.user_data["mag_upload_message_id"] = sent.message_id
    return MAG_UPLOAD_PHOTOS


async def mag_continue_from_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    photos = context.user_data.get("photos", [])
    if not photos:
        await query.edit_message_text(
            "⚠️ Нужно загрузить хотя бы одно фото перед продолжением.",
            parse_mode="HTML",
        )
        return MAG_UPLOAD_PHOTOS

    await query.edit_message_text(
        "📸 <b>Шаг 2/11: Фото с объекта</b>\n\n✅ Фото сохранены.",
        parse_mode="HTML",
    )

    await query.message.reply_text(
        "📍 <b>Шаг 3/11: Адрес</b>\n\nВведите адрес участка магистрали:",
        reply_markup=cancel_reply_keyboard(),
        parse_mode="HTML",
    )
    return MAG_ENTER_ADDRESS


async def mag_enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    data = _get_connection_data(context)
    data["address"] = text

    await update.message.reply_text(
        "📍 <b>Шаг 3/11: Адрес</b>\n\n✅ Адрес сохранен.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "📏 <b>Шаг 4/11: Метраж ВОЛС</b>\n\n"
        "Введите метраж (в метрах) или нажмите «Пропустить».",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return MAG_ENTER_FIBER


def _format_pieces(value: float) -> str:
    if not value:
        return "-"
    return f"{int(value) if float(value).is_integer() else round(value, 2)} шт."


async def _handle_float_step(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    data_key: str,
    step_title: str,
    next_prompt: str,
    next_state: int,
    allow_decimal: bool = True,
) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    value: float = 0.0
    if text == SKIP_TEXT:
        value = 0.0
    else:
        try:
            value = float(text.replace(",", "."))
            if value < 0:
                raise ValueError
            if not allow_decimal:
                value = float(int(value))
        except ValueError:
            await update.message.reply_text("Введите корректное число.")
            return next_state if next_state == MAG_ENTER_FIBER else next_state - 1

    data = _get_connection_data(context)
    data[data_key] = value

    await update.message.reply_text(
        f"{step_title}\n\n✅ Значение: {value if allow_decimal else _format_pieces(value)}",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        next_prompt,
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return next_state


async def mag_enter_fiber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    if text == SKIP_TEXT:
        value = 0.0
    else:
        try:
            value = float(text.replace(",", "."))
            if value < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Введите корректное число (например 120 или 75.5).")
            return MAG_ENTER_FIBER

    data = _get_connection_data(context)
    data["fiber_meters"] = value

    await update.message.reply_text(
        "📏 <b>Шаг 4/11: Метраж ВОЛС</b>\n\n✅ Значение сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "🪝 <b>Шаг 5/11: Крюки</b>\n\nУкажите количество крюков (шт.) или «Пропустить».",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return MAG_ENTER_HOOKS


async def mag_enter_hooks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    if text == SKIP_TEXT:
        value = 0
    else:
        try:
            value = int(float(text.replace(",", ".")))
            if value < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Введите целое число (например 5).")
            return MAG_ENTER_HOOKS

    data = _get_connection_data(context)
    data["hooks_quantity"] = float(value)

    await update.message.reply_text(
        "🪝 <b>Шаг 5/11: Крюки</b>\n\n✅ Значение сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "🔩 <b>Шаг 6/11: ОРК / ОРШ</b>\n\nУкажите количество (шт.) или «Пропустить».",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return MAG_ENTER_ORK


async def mag_enter_ork(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    if text == SKIP_TEXT:
        value = 0
    else:
        try:
            value = int(float(text.replace(",", ".")))
            if value < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Введите целое число (например 2).")
            return MAG_ENTER_ORK

    data = _get_connection_data(context)
    data["ork_quantity"] = float(value)

    await update.message.reply_text(
        "🔩 <b>Шаг 6/11: ОРК / ОРШ</b>\n\n✅ Значение сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "🧰 <b>Шаг 7/11: Муфты</b>\n\nУкажите количество (шт.) или «Пропустить».",
        reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
        parse_mode="HTML",
    )
    return MAG_ENTER_MUFTS


async def mag_enter_mufts(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    if text == SKIP_TEXT:
        value = 0
    else:
        try:
            value = int(float(text.replace(",", ".")))
            if value < 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("Введите целое число (например 1).")
            return MAG_ENTER_MUFTS

    data = _get_connection_data(context)
    data["mufta_quantity"] = float(value)

    await update.message.reply_text(
        "🧰 <b>Шаг 7/11: Муфты</b>\n\n✅ Значение сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    return await _start_sfp_step(update, context, db)


async def _start_sfp_step(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    names = await run_in_thread(db.get_all_sfp_module_names) or []
    data = _get_connection_data(context)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if not names:
        data["sfp_module_model"] = "-"
        data["sfp_module_quantity"] = 0
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🧿 <b>Шаг 8/11: SFP модули</b>\n\n⏭️ Модели отсутствуют, шаг пропущен.",
                parse_mode="HTML",
            )
        return await _start_comment_step(update, context)

    keyboard = [
        [InlineKeyboardButton(f"🧿 {name}", callback_data=f"mag_sfp_{name}")]
        for name in names
    ]
    keyboard.append([InlineKeyboardButton(SKIP_TEXT, callback_data="mag_sfp_skip")])
    reply_markup = build_inline_keyboard(keyboard)

    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "🧿 <b>Шаг 8/11: SFP модули</b>\n\n"
                "Выберите модель или пропустите шаг:"
            ),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )

    return MAG_SELECT_SFP


async def mag_select_sfp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = _get_connection_data(context)

    if query.data == "mag_sfp_skip":
        data["sfp_module_model"] = "-"
        data["sfp_module_quantity"] = 0
        await query.edit_message_text(
            "🧿 <b>Шаг 8/11: SFP модули</b>\n\n⏭️ Пропущено.",
            parse_mode="HTML",
        )
        return await _start_comment_step(update, context)

    if query.data == "cancel_connection":
        return await cancel_connection(update, context)

    if query.data.startswith("mag_sfp_"):
        model = query.data.replace("mag_sfp_", "", 1)
        data["sfp_module_model"] = model
        await query.edit_message_text(
            "🧿 <b>Шаг 8/11: SFP модули</b>\n\n"
            f"Выбрано: <b>{model}</b>. Укажите количество (шт.).",
            parse_mode="HTML",
        )
        await query.message.reply_text(
            "Введите количество SFP модулей:",
            reply_markup=cancel_reply_keyboard(),
        )
        return MAG_ENTER_SFP_QTY

    return MAG_SELECT_SFP


async def mag_enter_sfp_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    try:
        quantity = int(float(text.replace(",", ".")))
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля.")
        return MAG_ENTER_SFP_QTY

    data = _get_connection_data(context)
    data["sfp_module_quantity"] = quantity

    await update.message.reply_text(
        "🧿 <b>Шаг 8/11: SFP модули</b>\n\n✅ Значение сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    return await _start_comment_step(update, context)


async def _start_comment_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "💬 <b>Шаг 9/11: Комментарий</b>\n\n"
                "Добавьте комментарий или нажмите «Пропустить»."
            ),
            reply_markup=build_reply_keyboard([[SKIP_TEXT]], add_cancel=True),
            parse_mode="HTML",
        )
    return MAG_COMMENT


async def mag_enter_comment(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    text = (update.message.text or "").strip()
    if text in CANCEL_TEXT_VARIANTS:
        return await _cancel_flow(update, context)

    data = _get_connection_data(context)
    data["comment"] = "-" if text == SKIP_TEXT or not text else text

    await update.message.reply_text(
        "💬 <b>Шаг 9/11: Комментарий</b>\n\n✅ Сохранено.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )

    context.user_data["employee_step_label"] = "👥 <b>Шаг 10/11: Исполнители</b>"
    context.user_data["employee_selection_state"] = MAG_SELECT_EMPLOYEES
    return await start_employee_selection(update, context, db)
