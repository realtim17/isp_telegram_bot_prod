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
    ENTER_TWISTED_INTERNAL_AMOUNT,
    CONFIRM_MATERIAL_OPERATION,
    ENTER_OPERATION_COMMENT,
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
        from .start import return_to_manage_menu

        return await return_to_manage_menu(flow, update, context)

    emp_id = int(query.data.split("_")[2])
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    context.user_data["selected_employee_id"] = emp_id

    fiber = employee.get("fiber_balance", 0) or 0
    twisted_external = employee.get("twisted_pair_external_balance", 0) or 0
    twisted_internal = employee.get("twisted_pair_internal_balance", 0) or 0
    twisted_total = twisted_external + twisted_internal

    keyboard = [
        [InlineKeyboardButton("➕ Добавить материалы", callback_data="mat_action_add")],
        [InlineKeyboardButton("➖ Списать материалы", callback_data="mat_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="mat_back_to_list")],
    ]

    text = (
        "🧵 <b>ВОЛС / ВИТ.ПАРА</b>\n\n"
        f"👤 <b>Сотрудник:</b> {employee['full_name']}\n\n"
        "📊 <b>Текущий баланс:</b>\n"
        f"  • ВОЛС: {fiber} м\n"
        f"  • Витая пара (общая): {twisted_total} м\n"
        f"  • Внеш. витая пара: {twisted_external} м\n"
        f"  • Внут. витая пара: {twisted_internal} м\n\n"
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
                    f"🧵 {emp['full_name']} "
                    f"(ВОЛС: {emp.get('fiber_balance', 0) or 0}м, "
                    f"ВП: {(emp.get('twisted_pair_external_balance', 0) or 0) + (emp.get('twisted_pair_internal_balance', 0) or 0)}м)",
                    callback_data=f"mat_emp_{emp['id']}",
                )
            ]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "🧵 <b>ВОЛС / ВИТ.ПАРА</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL

    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    action = "add" if query.data == "mat_action_add" else "deduct"
    context.user_data["material_action"] = action

    verb = "Добавление" if action == "add" else "Списание"
    prefix = "➕" if action == "add" else "➖"
    await query.edit_message_text(
        f"{prefix} <b>{verb} материалов</b>\n\n"
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
        f"Теперь введите количество метров <b>внешней витой пары</b> для {verb}:\n"
        "(Введите 0, если не требуется)",
        parse_mode="HTML",
    )
    return ENTER_TWISTED_AMOUNT


async def enter_twisted_amount(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ввод значения внешней витой пары."""
    try:
        twisted_external_amount = float(update.message.text.strip().replace(",", "."))
        if twisted_external_amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED_AMOUNT

    context.user_data["twisted_external_amount"] = twisted_external_amount
    action = context.user_data.get("material_action")
    verb = "добавления" if action == "add" else "списания"
    await update.message.reply_text(
        f"✅ Внеш. витая пара: {twisted_external_amount} м\n\n"
        f"Теперь введите количество метров <b>внутренней витой пары</b> для {verb}:\n"
        "(Введите 0, если не требуется)",
        parse_mode="HTML",
    )
    return ENTER_TWISTED_INTERNAL_AMOUNT


async def enter_twisted_internal_amount(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ввод значения внутренней витой пары и подготовка подтверждения."""
    try:
        twisted_internal_amount = float(update.message.text.strip().replace(",", "."))
        if twisted_internal_amount < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED_INTERNAL_AMOUNT

    context.user_data["twisted_internal_amount"] = twisted_internal_amount
    context.user_data["twisted_amount"] = (
        context.user_data.get("twisted_external_amount", 0) + twisted_internal_amount
    )
    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    action = context.user_data.get("material_action")
    context.user_data.setdefault("material_comment", "")

    return await show_material_confirmation(flow, update.message, context, employee, action)


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
        context.user_data.pop("twisted_external_amount", None)
        context.user_data.pop("twisted_internal_amount", None)
        context.user_data.pop("twisted_amount", None)
        return ENTER_FIBER_AMOUNT
    
    if data == "material_comment":
        context.user_data["comment_target"] = "material"
        await query.edit_message_text(
            "📝 Введите комментарий к операции (например, причина списания или примечание):",
            parse_mode="HTML",
        )
        return ENTER_OPERATION_COMMENT

    if data != "material_confirm":
        return CONFIRM_MATERIAL_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    fiber_amount = context.user_data.get("fiber_amount", 0)
    twisted_external_amount = context.user_data.get("twisted_external_amount", 0)
    twisted_internal_amount = context.user_data.get("twisted_internal_amount", 0)
    twisted_amount = twisted_external_amount + twisted_internal_amount
    action = context.user_data.get("material_action")
    comment = context.user_data.get("material_comment", "")
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
            employee_id=emp_id,
            fiber_meters=fiber_amount,
            twisted_pair_external_meters=twisted_external_amount,
            twisted_pair_internal_meters=twisted_internal_amount,
            created_by=created_by,
            comment=comment,
        )
        if success:
            updated_emp = await run_in_thread(flow.db.get_employee_by_id, emp_id)
            new_fiber = updated_emp.get("fiber_balance", 0) or 0
            new_twisted_external = updated_emp.get("twisted_pair_external_balance", 0) or 0
            new_twisted_internal = updated_emp.get("twisted_pair_internal_balance", 0) or 0
            new_twisted_total = new_twisted_external + new_twisted_internal
            await query.edit_message_text(
                "✅ <b>Материалы добавлены!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"➕ Добавлено:\n  • ВОЛС: +{fiber_amount} м\n"
                f"  • Внеш. витая пара: +{twisted_external_amount} м\n"
                f"  • Внут. витая пара: +{twisted_internal_amount} м\n"
                f"  • Витая пара (общая): +{twisted_amount} м\n\n"
                f"📊 Новый баланс:\n  • ВОЛС: {new_fiber} м\n"
                f"  • Внеш. витая пара: {new_twisted_external} м\n"
                f"  • Внут. витая пара: {new_twisted_internal} м\n"
                f"  • Витая пара (общая): {new_twisted_total} м",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text("❌ Ошибка при добавлении материалов.")
    else:
        success = await run_in_thread(
            flow.db.deduct_material_from_employee,
            employee_id=emp_id,
            fiber_meters=fiber_amount,
            twisted_pair_external_meters=twisted_external_amount,
            twisted_pair_internal_meters=twisted_internal_amount,
            connection_id=None,
            created_by=created_by,
            comment=comment,
        )
        if success:
            updated_emp = await run_in_thread(flow.db.get_employee_by_id, emp_id)
            new_fiber = updated_emp.get("fiber_balance", 0) or 0
            new_twisted_external = updated_emp.get("twisted_pair_external_balance", 0) or 0
            new_twisted_internal = updated_emp.get("twisted_pair_internal_balance", 0) or 0
            new_twisted_total = new_twisted_external + new_twisted_internal
            await query.edit_message_text(
                "✅ <b>Материалы списаны!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"➖ Списано:\n  • ВОЛС: -{fiber_amount} м\n"
                f"  • Внеш. витая пара: -{twisted_external_amount} м\n"
                f"  • Внут. витая пара: -{twisted_internal_amount} м\n"
                f"  • Витая пара (общая): -{twisted_amount} м\n\n"
                f"📊 Новый баланс:\n  • ВОЛС: {new_fiber} м\n"
                f"  • Внеш. витая пара: {new_twisted_external} м\n"
                f"  • Внут. витая пара: {new_twisted_internal} м\n"
                f"  • Витая пара (общая): {new_twisted_total} м",
                parse_mode="HTML",
            )
        else:
            current_fiber = employee.get("fiber_balance", 0) or 0
            current_twisted_external = employee.get("twisted_pair_external_balance", 0) or 0
            current_twisted_internal = employee.get("twisted_pair_internal_balance", 0) or 0
            current_twisted_total = current_twisted_external + current_twisted_internal
            await query.edit_message_text(
                "❌ <b>Недостаточно материалов!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n\n"
                f"📊 Текущий баланс:\n  • ВОЛС: {current_fiber} м\n"
                f"  • Внеш. витая пара: {current_twisted_external} м\n"
                f"  • Внут. витая пара: {current_twisted_internal} м\n"
                f"  • Витая пара (общая): {current_twisted_total} м\n\n"
                f"❗ Требуется:\n  • ВОЛС: {fiber_amount} м\n"
                f"  • Внеш. витая пара: {twisted_external_amount} м\n"
                f"  • Внут. витая пара: {twisted_internal_amount} м\n"
                f"  • Витая пара (общая): {twisted_amount} м",
                parse_mode="HTML",
            )

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


def _material_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="material_confirm")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="material_edit")],
            [InlineKeyboardButton("📝 Добавить комментарий", callback_data="material_comment")],
            [InlineKeyboardButton("❌ Отмена", callback_data="material_cancel")],
        ]
    )


def _material_confirmation_text(
    employee_name: str,
    action: str,
    fiber_amount: float,
    twisted_external_amount: float,
    twisted_internal_amount: float,
    comment: str,
) -> str:
    sign = "+" if action == "add" else "-"
    action_word = "добавление" if action == "add" else "списание"
    comment_text = comment or "—"
    twisted_amount = twisted_external_amount + twisted_internal_amount
    return (
        f"👤 Сотрудник: <b>{employee_name}</b>\n"
        f"🧵 Действие: {action_word}\n\n"
        f"ВОЛС: {sign}{fiber_amount} м\n"
        f"Внеш. витая пара: {sign}{twisted_external_amount} м\n"
        f"Внут. витая пара: {sign}{twisted_internal_amount} м\n"
        f"Витая пара (общая): {sign}{twisted_amount} м\n"
        f"📝 Комментарий: {comment_text}\n\n"
        "Подтвердить операцию?"
    )


async def show_material_confirmation(flow: "EmployeeFlow", message, context: ContextTypes.DEFAULT_TYPE, employee: dict, action: str):
    text = _material_confirmation_text(
        employee.get("full_name", "—") if isinstance(employee, dict) else "—",
        action,
        context.user_data.get("fiber_amount", 0),
        context.user_data.get("twisted_external_amount", 0),
        context.user_data.get("twisted_internal_amount", 0),
        context.user_data.get("material_comment", ""),
    )
    await message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=_material_confirmation_keyboard(),
    )
    return CONFIRM_MATERIAL_OPERATION
