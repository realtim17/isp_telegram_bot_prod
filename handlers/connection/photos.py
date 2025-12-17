"""
Модуль обработки шага загрузки фотографий при создании подключения.
"""
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import UPLOAD_PHOTOS, ENTER_ADDRESS
from handlers.connection.constants import MAX_PHOTOS
from handlers.connection.ui import build_inline_keyboard, cancel_reply_keyboard


PHOTOS_STEP_HEADER = "📸 <b>Шаг 2/16: Загрузка фотографий</b>"


async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка загружаемых фотографий."""
    if update.message.photo:
        photos = context.user_data.get('photos', [])

        if len(photos) >= MAX_PHOTOS:
            await update.message.reply_text(f"⚠️ Достигнут лимит в {MAX_PHOTOS} фотографий.")
            return UPLOAD_PHOTOS

        photo_file_id = update.message.photo[-1].file_id
        photos.append(photo_file_id)
        context.user_data['photos'] = photos

        reply_markup = build_inline_keyboard([
            [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')]
        ])

        status_text = (
            f"{PHOTOS_STEP_HEADER}\n\n"
            f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
            "Можете загрузить еще фото или нажмите \"Продолжить\"."
        )

        if len(photos) == 1:
            sent_message = await update.message.reply_text(
                status_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            context.user_data['upload_message_id'] = sent_message.message_id
        else:
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data.get('upload_message_id'),
                    text=status_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            except Exception:
                sent_message = await update.message.reply_text(
                    status_text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                context.user_data['upload_message_id'] = sent_message.message_id

        return UPLOAD_PHOTOS

    return UPLOAD_PHOTOS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос адреса подключения после загрузки фото."""
    query = update.callback_query
    await query.answer()

    photos_count = len(context.user_data.get('photos', []))
    if photos_count == 0:
        await query.edit_message_text(
            "⚠️ <b>Ошибка:</b> Необходимо загрузить хотя бы одно фото!\n\n"
            "📸 Загрузите фотографии с места подключения.",
            parse_mode='HTML'
        )
        return UPLOAD_PHOTOS

    await query.edit_message_text(
        f"{PHOTOS_STEP_HEADER}\n\n"
        f"✅ Загружено фото: {photos_count}",
        parse_mode='HTML'
    )

    await query.message.reply_text(
        "📍 <b>Шаг 3/16: Адрес подключения</b>\n\n"
        "Введите адрес подключения абонента:",
        reply_markup=cancel_reply_keyboard(),
        parse_mode='HTML'
    )

    return ENTER_ADDRESS
