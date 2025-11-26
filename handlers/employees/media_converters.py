"""
Обработчики управления медиаконверторами сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_MEDIA,
    SELECT_MEDIA_ACTION,
    ENTER_MEDIA_NAME,
    ENTER_MEDIA_QUANTITY,
    CONFIRM_MEDIA_OPERATION,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread


async def _show_media_employee_list(flow: "EmployeeFlow", query) -> int:
    """Показать список сотрудников с остатками медиаконверторов"""
    employees = await run_in_thread(flow.db.get_all_employees)
    keyboard = []
    for emp in employees:
        devices = await run_in_thread(flow.db.get_employee_media_converters, emp["id"]) or []
        total_media = sum(device["quantity"] for device in devices)
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"🔄 {emp['full_name']} (МК: {total_media} шт.)",
                    callback_data=f"media_emp_{emp['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

    await query.edit_message_text(
        "🔄 <b>Медиаконверторы</b>\n\nВыберите сотрудника:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_EMPLOYEE_FOR_MEDIA


async def select_employee_for_media(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    emp_id = int(query.data.split("_")[-1])
    context.user_data["selected_employee_id"] = emp_id

    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    devices = await run_in_thread(flow.db.get_employee_media_converters, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    devices_text = (
        "\n".join(f"  • {dev['device_name']}: {dev['quantity']} шт." for dev in devices)
        if devices else "  Медиаконверторов нет"
    )

    keyboard = [
        [InlineKeyboardButton("➕ Добавить медиаконвертор", callback_data="media_action_add")],
        [InlineKeyboardButton("➖ Списать медиаконвертор", callback_data="media_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="media_back_to_list")],
    ]

    await query.edit_message_text(
        "🔄 <b>Медиаконверторы сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущий остаток:\n{devices_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_MEDIA_ACTION


async def select_media_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "media_back_to_list":
        return await _show_media_employee_list(flow, query)

    action = query.data.split("_")[-1]
    context.user_data["media_action"] = action

    if action == "add":
        keyboard = [
            [InlineKeyboardButton("🔄 Медик SNR 10/100/1000 Base-T", callback_data="media_model_Медик SNR 10/100/1000 Base-T")],
            [InlineKeyboardButton("✏️ Ввести вручную", callback_data="media_model_manual")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
        await query.edit_message_text(
            "➕ <b>Добавление медиаконверторов</b>\n\nВыберите модель или введите свою:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return ENTER_MEDIA_NAME

    emp_id = context.user_data.get("selected_employee_id")
    devices = await run_in_thread(flow.db.get_employee_media_converters, emp_id)
    if not devices:
        await query.edit_message_text("⚠️ У сотрудника нет медиаконверторов для списания.")
        return await _show_media_employee_list(flow, query)

    keyboard = [
        [InlineKeyboardButton(f"{dev['device_name']} ({dev['quantity']} шт.)",
                              callback_data=f"media_model_{dev['device_name']}")]
        for dev in devices
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

    await query.edit_message_text(
        "➖ <b>Списание медиаконвертора</b>\n\nВыберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_MEDIA_ACTION


async def enter_media_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "media_model_manual":
            await query.edit_message_text("✏️ Введите название медиаконвертора вручную:", parse_mode="HTML")
            return ENTER_MEDIA_NAME
        if query.data.startswith("media_model_"):
            context.user_data["media_name"] = query.data.replace("media_model_", "", 1)
            await query.edit_message_text("Введите количество (шт.):", parse_mode="HTML")
            return ENTER_MEDIA_QUANTITY
        if query.data == "manage_cancel":
            context.user_data.clear()
            await query.edit_message_text("❌ Операция отменена.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
    else:
        text = (update.message.text or "").strip()
        if len(text) < 2:
            await update.message.reply_text("Название должно содержать минимум 2 символа. Попробуйте снова.")
            return ENTER_MEDIA_NAME
        context.user_data["media_name"] = text
        await update.message.reply_text("Введите количество (шт.):")
        return ENTER_MEDIA_QUANTITY
    return ENTER_MEDIA_NAME


async def enter_media_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля (например, 1, 2, 3).")
        return ENTER_MEDIA_QUANTITY

    context.user_data["media_quantity"] = quantity
    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else None
    device_name = context.user_data.get("media_name")
    action = context.user_data.get("media_action", "add")
    sign = "+" if action == "add" else "-"
    action_word = "добавление" if action == "add" else "списание"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="media_confirm")],
            [InlineKeyboardButton("✏️ Изменить количество", callback_data="media_edit")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
    )
    await update.message.reply_text(
        "Проверьте данные и подтвердите операцию:\n\n"
        f"👤 Сотрудник: <b>{employee['full_name'] if employee else emp_id}</b>\n"
        f"🔄 Медиаконвертор: {device_name}\n"
        f"Действие: {action_word}\n"
        f"Количество: {sign}{quantity} шт.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )
    return CONFIRM_MEDIA_OPERATION


async def confirm_media_operation(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "media_edit":
        await query.edit_message_text("✏️ Введите количество заново:", parse_mode="HTML")
        context.user_data.pop("media_quantity", None)
        return ENTER_MEDIA_QUANTITY

    if data != "media_confirm":
        return CONFIRM_MEDIA_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    device_name = context.user_data.get("media_name")
    quantity = context.user_data.get("media_quantity", 0)
    action = context.user_data.get("media_action")
    created_by = query.from_user.id if query.from_user else None

    if not emp_id or not device_name or quantity <= 0:
        await query.edit_message_text("❌ Некорректные данные операции.")
        return ConversationHandler.END

    if action == "add":
        success = await run_in_thread(flow.db.add_media_converter_to_employee, emp_id, device_name, quantity, created_by)
    else:
        success = await run_in_thread(
            flow.db.deduct_media_converter_from_employee,
            emp_id,
            device_name,
            quantity,
            None,
            created_by,
        )

    if success:
        total = await run_in_thread(flow.db.get_media_converter_quantity, emp_id, device_name)
        emp = await run_in_thread(flow.db.get_employee_by_id, emp_id) or {}
        await query.edit_message_text(
            "✅ Медиаконверторы обновлены!\n\n"
            f"👤 Сотрудник: {emp.get('full_name', emp_id)}\n"
            f"🔄 Медиаконвертор: {device_name}\n"
            f"{'➕ Добавлено' if action == 'add' else '➖ Списано'}: {quantity} шт.\n"
            f"📊 Всего: {total} шт.",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❌ Не удалось выполнить операцию.")

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END
