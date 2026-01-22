"""
Обработчики управления ONU сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_ONU,
    SELECT_ONU_ACTION,
    ENTER_ONU_NAME,
    ENTER_ONU_QUANTITY,
    CONFIRM_ONU_OPERATION,
    ENTER_OPERATION_COMMENT,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread


async def _show_onu_employee_list(flow: "EmployeeFlow", query) -> int:
    """Показать список сотрудников с остатками ONU"""
    employees = await run_in_thread(flow.db.get_all_employees)
    keyboard = []
    for emp in employees:
        onu_devices = await run_in_thread(flow.db.get_employee_onu, emp["id"]) or []
        total_onu = sum(device["quantity"] for device in onu_devices)
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"🔌 {emp['full_name']} (ONU: {total_onu} шт.)",
                    callback_data=f"onu_emp_{emp['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

    await query.edit_message_text(
        "🔌 <b>ONU абон.терминалы</b>\n\nВыберите сотрудника:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_EMPLOYEE_FOR_ONU


async def select_employee_for_onu(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)

    emp_id = int(query.data.split("_")[-1])
    context.user_data["selected_employee_id"] = emp_id

    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    devices = await run_in_thread(flow.db.get_employee_onu, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    devices_text = (
        "\n".join(f"  • {dev['device_name']}: {dev['quantity']} шт." for dev in devices)
        if devices else "  Терминалов нет"
    )

    keyboard = [
        [InlineKeyboardButton("➕ Добавить ONU", callback_data="onu_action_add")],
        [InlineKeyboardButton("➖ Списать ONU", callback_data="onu_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="onu_back_to_list")],
    ]

    await query.edit_message_text(
        "🔌 <b>ONU сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущий остаток:\n{devices_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ONU_ACTION


async def select_onu_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "onu_back_to_list":
        return await _show_onu_employee_list(flow, query)

    action = query.data.split("_")[-1]
    context.user_data["onu_action"] = action

    if action == "add":
        keyboard = [
            [InlineKeyboardButton("🔌 ONU GPON 10/100/1000 Base-T", callback_data="onu_model_ONU GPON 10/100/1000 Base-T")],
            [InlineKeyboardButton("✏️ Ввести вручную", callback_data="onu_model_manual")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
        await query.edit_message_text(
            "➕ <b>Добавление ONU</b>\n\nВыберите модель или введите свою:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return ENTER_ONU_NAME

    emp_id = context.user_data.get("selected_employee_id")
    devices = await run_in_thread(flow.db.get_employee_onu, emp_id)
    if not devices:
        await query.edit_message_text("⚠️ У сотрудника нет ONU для списания.")
        return await _show_onu_employee_list(flow, query)

    keyboard = [
        [InlineKeyboardButton(f"{dev['device_name']} ({dev['quantity']} шт.)",
                              callback_data=f"onu_model_{dev['device_name']}")]
        for dev in devices
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

    await query.edit_message_text(
        "➖ <b>Списание ONU</b>\n\nВыберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ONU_ACTION


async def enter_onu_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "onu_model_manual":
            await query.edit_message_text("✏️ Введите название ONU вручную:", parse_mode="HTML")
            return ENTER_ONU_NAME
        if query.data.startswith("onu_model_"):
            context.user_data["onu_name"] = query.data.replace("onu_model_", "", 1)
            await query.edit_message_text("Введите количество ONU (шт.):", parse_mode="HTML")
            return ENTER_ONU_QUANTITY
        if query.data == "manage_cancel":
            context.user_data.clear()
            await query.edit_message_text("❌ Операция отменена.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
    else:
        text = (update.message.text or "").strip()
        if len(text) < 2:
            await update.message.reply_text("Название должно содержать минимум 2 символа. Попробуйте снова.")
            return ENTER_ONU_NAME
        context.user_data["onu_name"] = text
        await update.message.reply_text("Введите количество ONU (шт.):")
        return ENTER_ONU_QUANTITY
    return ENTER_ONU_NAME


async def enter_onu_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля (например, 1, 2, 3).")
        return ENTER_ONU_QUANTITY

    context.user_data["onu_quantity"] = quantity
    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else None
    device_name = context.user_data.get("onu_name")
    action = context.user_data.get("onu_action", "add")
    context.user_data.setdefault("onu_comment", "")
    return await show_onu_confirmation(update.message, employee, device_name, action, quantity, context)


async def confirm_onu_operation(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "onu_edit":
        await query.edit_message_text("✏️ Введите количество заново:", parse_mode="HTML")
        context.user_data.pop("onu_quantity", None)
        return ENTER_ONU_QUANTITY

    if data == "onu_comment":
        context.user_data["comment_target"] = "onu"
        await query.edit_message_text(
            "📝 Введите комментарий к операции с ONU:",
            parse_mode="HTML",
        )
        return ENTER_OPERATION_COMMENT

    if data != "onu_confirm":
        return CONFIRM_ONU_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    device_name = context.user_data.get("onu_name")
    quantity = context.user_data.get("onu_quantity", 0)
    action = context.user_data.get("onu_action")
    created_by = query.from_user.id if query.from_user else None
    comment = context.user_data.get("onu_comment", "")

    if not emp_id or not device_name or quantity <= 0:
        await query.edit_message_text("❌ Некорректные данные операции.")
        return ConversationHandler.END

    if action == "add":
        success = await run_in_thread(flow.db.add_onu_to_employee, emp_id, device_name, quantity, created_by, comment)
    else:
        success = await run_in_thread(
            flow.db.deduct_onu_from_employee,
            emp_id,
            device_name,
            quantity,
            None,
            created_by,
            comment,
        )

    if success:
        total = await run_in_thread(flow.db.get_onu_quantity, emp_id, device_name)
        emp = await run_in_thread(flow.db.get_employee_by_id, emp_id) or {}
        await query.edit_message_text(
            "✅ ONU обновлены!\n\n"
            f"👤 Сотрудник: {emp.get('full_name', emp_id)}\n"
            f"🔌 ONU: {device_name}\n"
            f"{'➕ Добавлено' if action == 'add' else '➖ Списано'}: {quantity} шт.\n"
            f"📊 Всего: {total} шт.",
            parse_mode="HTML"
        )
    else:
        await query.edit_message_text("❌ Не удалось выполнить операцию.")

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


def _onu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="onu_confirm")],
            [InlineKeyboardButton("✏️ Изменить количество", callback_data="onu_edit")],
            [InlineKeyboardButton("📝 Добавить комментарий", callback_data="onu_comment")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
    )


def _onu_confirmation_text(employee_name: str, device_name: str, quantity: int, action: str, comment: str) -> str:
    sign = "+" if action == "add" else "-"
    action_word = "добавление" if action == "add" else "списание"
    comment_text = comment or "—"
    return (
        "Проверьте данные и подтвердите операцию:\n\n"
        f"👤 Сотрудник: <b>{employee_name}</b>\n"
        f"🔌 ONU: {device_name}\n"
        f"Действие: {action_word}\n"
        f"Количество: {sign}{quantity} шт.\n"
        f"📝 Комментарий: {comment_text}"
    )


async def show_onu_confirmation(message, employee: dict, device_name: str, action: str, quantity: int, context: ContextTypes.DEFAULT_TYPE):
    text = _onu_confirmation_text(
        employee.get("full_name", "—") if employee else "—",
        device_name,
        quantity,
        action,
        context.user_data.get("onu_comment", ""),
    )
    await message.reply_text(
        text,
        reply_markup=_onu_keyboard(),
        parse_mode="HTML",
    )
    return CONFIRM_ONU_OPERATION
