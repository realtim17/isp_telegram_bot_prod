"""
Обработчики управления администраторами
"""
from __future__ import annotations

from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import MANAGE_ADMINS, ENTER_ADMIN_ID, logger
from utils.helpers import run_in_thread


def _admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Назначить администратора", callback_data="admin_add")],
        [InlineKeyboardButton("➖ Удалить администратора", callback_data="admin_remove")],
        [InlineKeyboardButton("📋 Список администраторов", callback_data="admin_list")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")],
    ])


async def show_admin_menu(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE,
                          notice: Optional[str] = None) -> int:
    """Показать меню управления администраторами"""
    if not flow.admin_manager:
        await _admins_not_configured(update)
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    entries = flow.admin_manager.list_entries()
    managed_count = sum(1 for entry in entries if entry.get("source") == "db")
    total = len(entries)

    text_parts = ["👑 <b>Управление администраторами</b>"]
    if notice:
        text_parts.append(notice)
    text_parts.append(f"Всего администраторов: <b>{total}</b>")
    text_parts.append(f"Назначено через бота: <b>{managed_count}</b>")
    text_parts.append("\nВыберите действие:")
    text = "\n\n".join(text_parts)

    message = update.effective_message
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_admin_menu_keyboard(), parse_mode="HTML")
    else:
        await message.reply_text(text, reply_markup=_admin_menu_keyboard(), parse_mode="HTML")
    return MANAGE_ADMINS


async def handle_admin_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = query.data

    if data == "back_to_manage":
        await query.answer()
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    if not flow.admin_manager:
        await _admins_not_configured(update)
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    if data in {"admin_menu", "admin_back_to_menu"}:
        await query.answer()
        return await show_admin_menu(flow, update, context)

    if data == "admin_add":
        return await _prompt_admin_add(query)

    if data == "admin_list":
        return await _show_admin_list(flow, update)

    if data == "admin_remove":
        return await _show_remove_list(flow, update)

    if data.startswith("revoke_admin_"):
        user_id = int(data.replace("revoke_admin_", "", 1))
        success, error = await run_in_thread(flow.admin_manager.remove_admin, user_id)
        if success:
            await query.answer("Администратор удален")
            return await show_admin_menu(flow, update, context)
        await query.answer(error or "Не удалось удалить", show_alert=True)
        return MANAGE_ADMINS

    await query.answer("Неизвестное действие", show_alert=True)
    return MANAGE_ADMINS


async def enter_admin_user_id(flow: "EmployeeFlow", update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода ID администратора"""
    if not flow.admin_manager:
        await update.message.reply_text("⚠️ Управление администраторами недоступно.")
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    text = (update.message.text or "").strip()
    if text.lower() in {"отмена", "cancel"}:
        return await show_admin_menu(flow, update, context, "Операция отменена.")

    parts = text.split(maxsplit=1)
    try:
        user_id = int(parts[0])
    except (ValueError, IndexError):
        await update.message.reply_text("Введите числовой ID пользователя. Можно добавить комментарий после ID.")
        return ENTER_ADMIN_ID

    title = parts[1].strip() if len(parts) > 1 else None
    created_by = update.effective_user.id if update.effective_user else None

    success, error = await run_in_thread(flow.admin_manager.add_admin, user_id, title, created_by)
    if success:
        await update.message.reply_text(f"✅ Пользователь <b>{user_id}</b> назначен администратором.", parse_mode="HTML")
        return await show_admin_menu(flow, update, context)

    await update.message.reply_text(error or "Не удалось назначить администратора. Попробуйте снова.")
    return ENTER_ADMIN_ID


async def _prompt_admin_add(query) -> int:
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_menu")],
        [InlineKeyboardButton("❌ Отмена", callback_data="back_to_manage")],
    ])
    await query.edit_message_text(
        "➕ <b>Назначение администратора</b>\n\n"
        "Отправьте ID пользователя, которого нужно назначить администратором.\n"
        "Можно добавить комментарий: <code>12345 Иван Иванов</code>.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return ENTER_ADMIN_ID


async def _show_admin_list(flow: "EmployeeFlow", update: Update) -> int:
    query = update.callback_query
    entries = flow.admin_manager.list_entries()
    if not entries:
        text = "👑 <b>Администраторы не назначены.</b>\n\nДобавьте первого через кнопку «Назначить администратора»."
    else:
        lines = ["👑 <b>Список администраторов</b>\n"]
        for idx, entry in enumerate(entries, 1):
            source = "(.env)" if entry.get("source") == "env" else ""
            title = entry.get("title") or "—"
            lines.append(f"{idx}. <b>{entry['user_id']}</b> {source}\n   {title}")
        text = "\n".join(lines)

    await query.answer()
    await query.edit_message_text(text, reply_markup=_admin_menu_keyboard(), parse_mode="HTML")
    return MANAGE_ADMINS


async def _show_remove_list(flow: "EmployeeFlow", update: Update) -> int:
    query = update.callback_query
    entries = flow.admin_manager.list_entries()
    removable = [entry for entry in entries if entry.get("removable")]
    if not removable:
        await query.answer("Нет администраторов, назначенных через бота.", show_alert=True)
        return MANAGE_ADMINS

    keyboard = [
        [InlineKeyboardButton(f"{entry['user_id']} • {entry.get('title') or '—'}",
                              callback_data=f"revoke_admin_{entry['user_id']}")]
        for entry in removable
    ]
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back_to_menu")])

    await query.answer()
    await query.edit_message_text(
        "➖ <b>Удаление администратора</b>\n\nВыберите пользователя:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return MANAGE_ADMINS


async def _admins_not_configured(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("⚠️ Управление администраторами временно недоступно.")
    else:
        logger.warning("Попытка открыть управление администраторами без менеджера.")
