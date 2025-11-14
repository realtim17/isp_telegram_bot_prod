"""
Обработчики управления материалами сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_MATERIAL,
    SELECT_MATERIAL_ACTION,
    ENTER_FIBER_AMOUNT,
    ENTER_TWISTED_AMOUNT,
    CONFIRM_MATERIAL_OPERATION,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread


async def select_employee_for_material(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Выбор сотрудника для операций с материалами"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import manage_employees_start

        return await manage_employees_start(flow, update, context)

    emp_id = int(query.data.split("_")[2])
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    context.user_data["selected_employee_id"] = emp_id

    fiber = employee.get("fiber_balance", 0) or 0
    twisted = employee.get("twisted_pair_balance", 0) or 0

    keyboard = [
        [InlineKeyboardButton("➕ Добавить материалы", callback_data="mat_action_add")],
        [InlineKeyboardButton("➖ Списать материалы", callback_data="mat_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="mat_back_to_list")],
    ]

    text = (
        "📦 <b>Управление материалами</b>\n\n"
        f"👤 <b>Сотрудник:</b> {employee['full_name']}\n\n"
        "📊 <b>Текущий баланс:</b>\n"
        f"  • ВОЛС: {fiber} м\n"
        f"  • Витая пара: {twisted} м\n\n"
        "Выберите действие:"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_MATERIAL_ACTION


async def select_material_action(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Обработка выбора действия с материалами"""
    query = update.callback_query
    await query.answer()

    if query.data == "mat_back_to_list":
        employees = await run_in_thread(flow.db.get_all_employees)
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📦 {emp['full_name']} "
                    f"(ВОЛС: {emp.get('fiber_balance', 0) or 0}м, "
                    f"ВП: {emp.get('twisted_pair_balance', 0) or 0}м)",
                    callback_data=f"mat_emp_{emp['id']}",
                )
            ]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "📦 <b>Управление материалами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL

    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    action = "add" if query.data == "mat_action_add" else "deduct"
    context.user_data["material_action"] = action

    verb = "Добавление" if action == "add" else "Списание"
    await query.edit_message_text(
        f"➕ <b>{verb} материалов</b>\n\n"
        f"👤 Сотрудник: {employee['full_name']}\n\n"
        "Введите количество метров <b>ВОЛС</b>:\n"
        "(Введите 0, если не требуется)",
        parse_mode="HTML",
    )
    return ENTER_FIBER_AMOUNT


async def enter_fiber_amount(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ввод значения ВОЛС"""
    try:
        fiber_amount = float(update.message.text.strip().replace(",", "."))
        if fiber_amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_FIBER_AMOUNT

    context.user_data["fiber_amount"] = fiber_amount
    action = context.user_data.get("material_action")
    verb = "добавления" if action == "add" else "списания"

    await update.message.reply_text(
        f"✅ ВОЛС: {fiber_amount} м\n\n"
        f"Теперь введите количество метров <b>витой пары</b> для {verb}:\n"
        "(Введите 0, если не требуется)",
        parse_mode="HTML",
    )
    return ENTER_TWISTED_AMOUNT


async def enter_twisted_amount(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ввод значения витой пары и подготовка подтверждения"""
    try:
        twisted_amount = float(update.message.text.strip().replace(",", "."))
        if twisted_amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED_AMOUNT

    context.user_data["twisted_amount"] = twisted_amount
    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    action = context.user_data.get("material_action")
    sign = "+" if action == "add" else "-"

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="material_confirm")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="material_edit")],
            [InlineKeyboardButton("❌ Отмена", callback_data="material_cancel")],
        ]
    )

    await update.message.reply_text(
        f"👤 Сотрудник: <b>{employee['full_name']}</b>\n"
        f"📦 Действие: {'добавление' if sign == '+' else 'списание'}\n\n"
        f"ВОЛС: {sign}{context.user_data.get('fiber_amount', 0)} м\n"
        f"Витая пара: {sign}{twisted_amount} м\n\n"
        "Подтвердить операцию?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return CONFIRM_MATERIAL_OPERATION


async def confirm_material_operation(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Подтверждение операции с материалами"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "material_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция с материалами отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "material_edit":
        await query.edit_message_text(
            "✏️ Введите количество метров ВОЛС заново:",
            parse_mode="HTML",
        )
        context.user_data.pop("fiber_amount", None)
        context.user_data.pop("twisted_amount", None)
        return ENTER_FIBER_AMOUNT

    if data != "material_confirm":
        return CONFIRM_MATERIAL_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    fiber_amount = context.user_data.get("fiber_amount", 0)
    twisted_amount = context.user_data.get("twisted_amount", 0)
    action = context.user_data.get("material_action")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        context.user_data.clear()
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    created_by = query.from_user.id if query and query.from_user else None

    if action == "add":
        success = await run_in_thread(
            flow.db.add_material_to_employee,
            emp_id,
            fiber_amount,
            twisted_amount,
            created_by,
        )
        if success:
            updated_emp = await run_in_thread(flow.db.get_employee_by_id, emp_id)
            new_fiber = updated_emp.get("fiber_balance", 0) or 0
            new_twisted = updated_emp.get("twisted_pair_balance", 0) or 0
            await query.edit_message_text(
                "✅ <b>Материалы добавлены!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"➕ Добавлено:\n  • ВОЛС: +{fiber_amount} м\n  • Витая пара: +{twisted_amount} м\n\n"
                f"📊 Новый баланс:\n  • ВОЛС: {new_fiber} м\n  • Витая пара: {new_twisted} м",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text("❌ Ошибка при добавлении материалов.")
    else:
        success = await run_in_thread(
            flow.db.deduct_material_from_employee,
            emp_id,
            fiber_amount,
            twisted_amount,
            None,
            created_by,
        )
        if success:
            updated_emp = await run_in_thread(flow.db.get_employee_by_id, emp_id)
            new_fiber = updated_emp.get("fiber_balance", 0) or 0
            new_twisted = updated_emp.get("twisted_pair_balance", 0) or 0
            await query.edit_message_text(
                "✅ <b>Материалы списаны!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"➖ Списано:\n  • ВОЛС: -{fiber_amount} м\n  • Витая пара: -{twisted_amount} м\n\n"
                f"📊 Новый баланс:\n  • ВОЛС: {new_fiber} м\n  • Витая пара: {new_twisted} м",
                parse_mode="HTML",
            )
        else:
            current_fiber = employee.get("fiber_balance", 0) or 0
            current_twisted = employee.get("twisted_pair_balance", 0) or 0
            await query.edit_message_text(
                "❌ <b>Недостаточно материалов!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"📊 Текущий баланс:\n  • ВОЛС: {current_fiber} м\n  • Витая пара: {current_twisted} м\n\n"
                f"❗ Требуется:\n  • ВОЛС: {fiber_amount} м\n  • Витая пара: {twisted_amount} м",
                parse_mode="HTML",
            )

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END
