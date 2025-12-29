"""
Управление SNR оптическими боксами сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_SNR,
    SELECT_SNR_ACTION,
    ENTER_SNR_NAME,
    ENTER_SNR_QUANTITY,
    CONFIRM_SNR_OPERATION,
    ENTER_OPERATION_COMMENT,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread

SNR_PRESET_MODELS = [
    "Кросс оптический SNR",
]


async def select_employee_for_snr(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_manage":
        from .start import return_to_manage_menu
        return await return_to_manage_menu(flow, update, context)
    
    emp_id = int(query.data.split("_")[-1])
    context.user_data["snr_selected_employee_id"] = emp_id
    
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    snr_boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp_id)
    
    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    if snr_boxes:
        box_lines = "\n".join(f"  • {box['box_name']}: {box['quantity']} шт." for box in snr_boxes)
    else:
        box_lines = "  Боксов нет"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить бокс", callback_data="snr_action_add")],
        [InlineKeyboardButton("➖ Списать бокс", callback_data="snr_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="snr_back_to_list")],
    ]
    
    await query.edit_message_text(
        "🧰 <b>SNR боксы сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущие боксы:\n{box_lines}\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return SELECT_SNR_ACTION


async def select_snr_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "snr_back_to_list":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        
        keyboard = []
        for emp in employees:
            snr_boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp["id"])
            total = sum(box["quantity"] for box in snr_boxes)
            info = f"{total} шт." if total > 0 else "нет"
            keyboard.append(
                [InlineKeyboardButton(f"🧰 {emp['full_name']} ({info})", callback_data=f"snr_emp_{emp['id']}")]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])
        
        await query.edit_message_text(
            "🧰 <b>Управление SNR боксами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_SNR
    
    action = query.data.split("_")[-1]
    context.user_data["snr_action"] = action
    
    if action == "add":
        keyboard = [
            [InlineKeyboardButton(f"🧰 {name}", callback_data=f"snr_model_{name}")]
            for name in SNR_PRESET_MODELS
        ]
        keyboard.append([InlineKeyboardButton("✏️ Ввести вручную", callback_data="snr_model_manual")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])
        await query.edit_message_text(
            "➕ <b>Добавление боксов</b>\n\nВыберите модель или введите вручную:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return ENTER_SNR_NAME
    
    emp_id = context.user_data.get("snr_selected_employee_id")
    snr_boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp_id)
    if not snr_boxes:
        await query.edit_message_text("⚠️ У сотрудника нет боксов для списания.")
        return await select_employee_for_snr(flow, update, context)
    
    keyboard = [
        [InlineKeyboardButton(f"🧰 {box['box_name']} ({box['quantity']} шт.)", callback_data=f"snr_model_{box['box_name']}")]
        for box in snr_boxes
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])
    await query.edit_message_text(
        "➖ <b>Списание боксов</b>\n\nВыберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return ENTER_SNR_NAME


async def enter_snr_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "snr_model_manual":
            await query.edit_message_text("✏️ Введите название бокса вручную:", parse_mode="HTML")
            return ENTER_SNR_NAME
        if query.data.startswith("snr_model_"):
            context.user_data["snr_box_name"] = query.data.replace("snr_model_", "")
            await query.edit_message_text("Введите количество боксов (шт.):", parse_mode="HTML")
            return ENTER_SNR_QUANTITY
        if query.data == "manage_cancel":
            context.user_data.clear()
            await query.edit_message_text("❌ Операция отменена.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
    else:
        text = (update.message.text or "").strip()
        if len(text) < 2:
            await update.message.reply_text("Название должно содержать минимум 2 символа. Попробуйте снова.")
            return ENTER_SNR_NAME
        context.user_data["snr_box_name"] = text
        await update.message.reply_text("Введите количество боксов (шт.):")
        return ENTER_SNR_QUANTITY
    return ENTER_SNR_NAME


async def enter_snr_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля (например, 1, 2, 3).")
        return ENTER_SNR_QUANTITY
    
    context.user_data["snr_box_quantity"] = quantity
    emp_id = context.user_data.get("snr_selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else None
    action = context.user_data.get("snr_action", "add")
    box_name = context.user_data.get("snr_box_name")
    context.user_data.setdefault("snr_comment", "")
    return await show_snr_confirmation(update.message, employee, box_name, action, quantity, context)


async def confirm_snr_operation(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data == "snr_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    if data == "snr_edit":
        await query.edit_message_text("✏️ Введите количество заново:", parse_mode="HTML")
        context.user_data.pop("snr_box_quantity", None)
        return ENTER_SNR_QUANTITY
    
    if data == "snr_comment":
        context.user_data["comment_target"] = "snr"
        await query.edit_message_text(
            "📝 Введите комментарий к операции с боксом:",
            parse_mode="HTML",
        )
        return ENTER_OPERATION_COMMENT
    
    if data != "snr_confirm":
        return CONFIRM_SNR_OPERATION
    
    emp_id = context.user_data.get("snr_selected_employee_id")
    box_name = context.user_data.get("snr_box_name")
    quantity = context.user_data.get("snr_box_quantity", 0)
    action = context.user_data.get("snr_action")
    comment = context.user_data.get("snr_comment", "")
    
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        context.user_data.clear()
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    created_by = query.from_user.id if query and query.from_user else None
    if action == "add":
        success = await run_in_thread(flow.db.add_snr_box_to_employee, emp_id, box_name, quantity, created_by, comment)
        if success:
            new_qty = await run_in_thread(flow.db.get_snr_box_quantity, emp_id, box_name)
            text = (
                "✅ <b>Боксы добавлены!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"🧰 Бокс: {box_name}\n"
                f"➕ Добавлено: {quantity} шт.\n"
                f"📊 Всего: {new_qty} шт."
            )
        else:
            text = "❌ Ошибка при добавлении боксов."
    else:
        success = await run_in_thread(
            flow.db.deduct_snr_box_from_employee,
            emp_id,
            box_name,
            quantity,
            None,
            created_by,
            comment,
        )
        if success:
            new_qty = await run_in_thread(flow.db.get_snr_box_quantity, emp_id, box_name)
            text = (
                "✅ <b>Боксы списаны!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"🧰 Бокс: {box_name}\n"
                f"➖ Списано: {quantity} шт.\n"
                f"📊 Осталось: {new_qty} шт."
            )
        else:
            text = "❌ Ошибка при списании (недостаточно на балансе)."
    
    await query.edit_message_text(text, parse_mode="HTML")
    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


def _snr_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="snr_confirm")],
            [InlineKeyboardButton("✏️ Изменить количество", callback_data="snr_edit")],
            [InlineKeyboardButton("📝 Добавить комментарий", callback_data="snr_comment")],
            [InlineKeyboardButton("❌ Отмена", callback_data="snr_cancel")],
        ]
    )


def _snr_confirmation_text(employee_name: str, box_name: str, quantity: int, action: str, comment: str) -> str:
    action_word = "добавление" if action == "add" else "списание"
    sign = "+" if action == "add" else "-"
    comment_text = comment or "—"
    return (
        "Проверьте данные и подтвердите операцию:\n\n"
        f"👤 Сотрудник: <b>{employee_name}</b>\n"
        f"🧰 Бокс: {box_name}\n"
        f"Действие: {action_word}\n"
        f"Количество: {sign}{quantity} шт.\n"
        f"📝 Комментарий: {comment_text}"
    )


async def show_snr_confirmation(message, employee: dict, box_name: str, action: str, quantity: int, context: ContextTypes.DEFAULT_TYPE):
    text = _snr_confirmation_text(
        employee.get("full_name", "—") if employee else "—",
        box_name,
        quantity,
        action,
        context.user_data.get("snr_comment", ""),
    )
    await message.reply_text(
        text,
        reply_markup=_snr_keyboard(),
        parse_mode="HTML",
    )
    return CONFIRM_SNR_OPERATION
