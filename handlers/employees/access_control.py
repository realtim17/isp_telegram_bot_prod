"""
Обработчики управления доступом к боту
"""
from __future__ import annotations

from typing import Optional, List, Dict

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import MANAGE_ACCESS, ENTER_ACCESS_ID, logger
from utils.helpers import run_in_thread


def _access_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Выдать доступ", callback_data="access_add")],
        [InlineKeyboardButton("➖ Отозвать доступ", callback_data="access_remove")],
        [InlineKeyboardButton("📋 Список доступа", callback_data="access_list")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")],
    ])


async def show_access_menu(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE,
                           notice: Optional[str] = None) -> int:
    """Показать главное меню управления доступом"""
    if not flow.access_manager:
        await _access_not_configured(update)
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    entries = flow.access_manager.list_entries()
    managed_count = sum(1 for entry in entries if entry.get("source") == "db")
    total = len(entries)

    text_parts = ["🔐 <b>Управление доступом</b>"]
    if notice:
        text_parts.append(notice)
    text_parts.append(f"Всего ID с доступом: <b>{total}</b>")
    text_parts.append(f"Выдано через бота: <b>{managed_count}</b>")
    text_parts.append("\nВыберите действие:")
    text = "\n\n".join(text_parts)

    message = update.effective_message
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_access_menu_keyboard(), parse_mode="HTML")
    else:
        await message.reply_text(text, reply_markup=_access_menu_keyboard(), parse_mode="HTML")
    return MANAGE_ACCESS


async def handle_access_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нажатий в меню доступа"""
    query = update.callback_query
    data = query.data

    if data == "back_to_manage":
        await query.answer()
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    if not flow.access_manager:
        await _access_not_configured(update)
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    if data == "access_menu" or data == "access_back_to_menu":
        await query.answer()
        return await show_access_menu(flow, update, context)

    if data == "access_add":
        await query.answer()
        return await _prompt_access_add(query)

    if data == "access_list":
        return await _show_access_list(flow, update)

    if data == "access_remove":
        return await _show_remove_list(flow, update)

    if data.startswith("revoke_access_"):
        user_id = int(data.replace("revoke_access_", "", 1))
        success, error = await run_in_thread(flow.access_manager.remove_user, user_id)
        if success:
            await query.answer("Доступ удален")
            return await show_access_menu(flow, update, context)
        await query.answer(error or "Не удалось удалить", show_alert=True)
        return MANAGE_ACCESS

    await query.answer("Неизвестное действие", show_alert=True)
    return MANAGE_ACCESS


async def enter_access_user_id(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода ID пользователя"""
    if not flow.access_manager:
        await update.message.reply_text("⚠️ Управление доступом недоступно.")
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    text = (update.message.text or "").strip()
    lower_text = text.lower()
    if lower_text in {"отмена", "cancel"}:
        return await show_access_menu(flow, update, context, "Операция отменена.")

    parts = text.split(maxsplit=1)
    try:
        user_id = int(parts[0])
    except (ValueError, IndexError):
        await update.message.reply_text("Введите числовой ID (например, 123456). Можно добавить комментарий после ID.")
        return ENTER_ACCESS_ID

    title = parts[1].strip() if len(parts) > 1 else None
    created_by = update.effective_user.id if update.effective_user else None

    success, error = await run_in_thread(flow.access_manager.add_user, user_id, title, created_by)
    if success:
        await update.message.reply_text(f"✅ Доступ выдан для ID <b>{user_id}</b>.", parse_mode="HTML")
        return await show_access_menu(flow, update, context)

    await update.message.reply_text(error or "Не удалось сохранить ID. Попробуйте снова или нажмите «Назад».")
    return ENTER_ACCESS_ID


async def _prompt_access_add(query) -> int:
    """Показать форму ввода ID"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="access_back_to_menu")],
        [InlineKeyboardButton("❌ Отмена", callback_data="back_to_manage")],
    ])
    await query.edit_message_text(
        "➕ <b>Выдача доступа</b>\n\n"
        "Отправьте ID пользователя, которому нужно разрешить работу с ботом.\n"
        "Можно добавить комментарий после ID, например: <code>12345 Иван Иванов</code>.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return ENTER_ACCESS_ID


async def _show_access_list(flow: "EmployeeFlow", update: Update) -> int:
    """Показать полный список ID"""
    query = update.callback_query
    entries = flow.access_manager.list_entries()
    if not entries:
        text = "🔐 <b>Список доступа пуст.</b>\n\nДобавьте первый ID через кнопку «Выдать доступ»."
    else:
        lines = ["🔐 <b>Список доступа</b>\n"]
        for idx, entry in enumerate(entries, 1):
            title = entry.get("title") or "—"
            source = "(.env)" if entry.get("source") == "env" else ""
            lines.append(f"{idx}. <b>{entry['user_id']}</b> {source}\n   {title}")
        text = "\n".join(lines)

    await query.answer()
    await query.edit_message_text(text, reply_markup=_access_menu_keyboard(), parse_mode="HTML")
    return MANAGE_ACCESS


async def _show_remove_list(flow: "EmployeeFlow", update: Update) -> int:
    """Показать список ID для удаления"""
    query = update.callback_query
    entries = flow.access_manager.list_entries()
    removable = [entry for entry in entries if entry.get("removable")]
    if not removable:
        await query.answer("Нет ID, выданных через бота.", show_alert=True)
        return MANAGE_ACCESS

    keyboard = [
        [InlineKeyboardButton(f"{entry['user_id']} • {entry.get('title') or '—'}",
                              callback_data=f"revoke_access_{entry['user_id']}")]
        for entry in removable
    ]
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="access_back_to_menu")])

    await query.answer()
    await query.edit_message_text(
        "➖ <b>Отзыв доступа</b>\n\nВыберите ID, который нужно удалить:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return MANAGE_ACCESS


async def _access_not_configured(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("⚠️ Управление доступом временно недоступно.")
    else:
        logger.warning("Попытка открыть доступ без настроенного менеджера.")
