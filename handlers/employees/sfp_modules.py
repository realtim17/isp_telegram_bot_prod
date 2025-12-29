"""
Обработчики управления SFP модулями сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_SFP,
    SELECT_SFP_ACTION,
    ENTER_SFP_NAME,
    ENTER_SFP_QUANTITY,
    CONFIRM_SFP_OPERATION,
    ENTER_OPERATION_COMMENT,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread

SFP_PRESET_MODELS = [
    "SFP модуль",
]


async def _show_sfp_employee_list(flow: "EmployeeFlow", query) -> int:
    """Показать сотрудников и их остатки SFP модулей"""
    employees = await run_in_thread(flow.db.get_all_employees)
    keyboard = []
    for emp in employees:
        modules = await run_in_thread(flow.db.get_employee_sfp_modules, emp["id"]) or []
        total = sum(item["quantity"] for item in modules)
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"🧿 {emp['full_name']} (SFP: {total} шт.)",
                    callback_data=f"sfp_emp_{emp['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

    await query.edit_message_text(
        "🧿 <b>SFP модули</b>\n\nВыберите сотрудника:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_EMPLOYEE_FOR_SFP
async def select_employee_for_sfp(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import return_to_manage_menu

        return await return_to_manage_menu(flow, update, context)

    emp_id = int(query.data.split("_")[-1])
    context.user_data["selected_employee_id"] = emp_id

    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    modules = await run_in_thread(flow.db.get_employee_sfp_modules, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    modules_text = (
        "\n".join(f"  • {dev['module_name']}: {dev['quantity']} шт." for dev in modules)
        if modules
        else "  Модулей нет"
    )

    keyboard = [
        [InlineKeyboardButton("➕ Добавить SFP", callback_data="sfp_action_add")],
        [InlineKeyboardButton("➖ Списать SFP", callback_data="sfp_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="sfp_back_to_list")],
    ]

    await query.edit_message_text(
        "🧿 <b>SFP модули сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущий остаток:\n{modules_text}\n\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_SFP_ACTION


async def select_sfp_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if query.data == "sfp_back_to_list":
        return await _show_sfp_employee_list(flow, query)

    action = query.data.split("_")[-1]
    context.user_data["sfp_action"] = action

    if action == "add":
        keyboard = [
            [InlineKeyboardButton(f"🧿 {name}", callback_data=f"sfp_model_{name}")]
            for name in SFP_PRESET_MODELS
        ]
        keyboard.append([InlineKeyboardButton("✏️ Ввести вручную", callback_data="sfp_model_manual")])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

        await query.edit_message_text(
            "➕ <b>Добавление SFP</b>\n\nВыберите модель или введите свою:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return ENTER_SFP_NAME

    emp_id = context.user_data.get("selected_employee_id")
    modules = await run_in_thread(flow.db.get_employee_sfp_modules, emp_id)
    if not modules:
        await query.edit_message_text("⚠️ У сотрудника нет SFP модулей для списания.")
        return await _show_sfp_employee_list(flow, query)

    keyboard = [
        [
            InlineKeyboardButton(
                f"🧿 {item['module_name']} ({item['quantity']} шт.)",
                callback_data=f"sfp_model_{item['module_name']}",
            )
        ]
        for item in modules
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

    await query.edit_message_text(
        "➖ <b>Списание SFP</b>\n\nВыберите модель:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_SFP_ACTION


async def enter_sfp_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "sfp_model_manual":
            await query.edit_message_text("✏️ Введите название SFP модуля вручную:", parse_mode="HTML")
            return ENTER_SFP_NAME
        if query.data.startswith("sfp_model_"):
            context.user_data["sfp_name"] = query.data.replace("sfp_model_", "", 1)
            await query.edit_message_text("Введите количество (шт.):", parse_mode="HTML")
            return ENTER_SFP_QUANTITY
        if query.data == "manage_cancel":
            context.user_data.clear()
            await query.edit_message_text("❌ Операция отменена.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
    else:
        text = (update.message.text or "").strip()
        if len(text) < 2:
            await update.message.reply_text("Название должно содержать минимум 2 символа. Попробуйте снова.")
            return ENTER_SFP_NAME
        context.user_data["sfp_name"] = text
        await update.message.reply_text("Введите количество (шт.):")
        return ENTER_SFP_QUANTITY
    return ENTER_SFP_NAME


async def enter_sfp_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Введите целое число больше нуля (например, 1, 2, 3).")
        return ENTER_SFP_QUANTITY

    context.user_data["sfp_quantity"] = quantity
    emp_id = context.user_data.get("selected_employee_id")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else None
    module_name = context.user_data.get("sfp_name")
    action = context.user_data.get("sfp_action", "add")
    context.user_data.setdefault("sfp_comment", "")
    return await show_sfp_confirmation(update.message, employee, module_name, action, quantity, context)


async def confirm_sfp_operation(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "manage_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "sfp_edit":
        await query.edit_message_text("✏️ Введите количество заново:", parse_mode="HTML")
        context.user_data.pop("sfp_quantity", None)
        return ENTER_SFP_QUANTITY

    if data == "sfp_comment":
        context.user_data["comment_target"] = "sfp"
        await query.edit_message_text("📝 Введите комментарий к операции с SFP:", parse_mode="HTML")
        return ENTER_OPERATION_COMMENT

    if data != "sfp_confirm":
        return CONFIRM_SFP_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    module_name = context.user_data.get("sfp_name")
    quantity = context.user_data.get("sfp_quantity", 0)
    action = context.user_data.get("sfp_action")
    created_by = query.from_user.id if query.from_user else None
    comment = context.user_data.get("sfp_comment", "")

    if not emp_id or not module_name or quantity <= 0:
        await query.edit_message_text("❌ Некорректные данные операции.")
        return ConversationHandler.END

    if action == "add":
        success = await run_in_thread(flow.db.add_sfp_module_to_employee, emp_id, module_name, quantity, created_by, comment)
    else:
        success = await run_in_thread(
            flow.db.deduct_sfp_module_from_employee,
            emp_id,
            module_name,
            quantity,
            None,
            created_by,
            comment,
        )

    if success:
        total = await run_in_thread(flow.db.get_sfp_module_quantity, emp_id, module_name)
        emp = await run_in_thread(flow.db.get_employee_by_id, emp_id) or {}
        await query.edit_message_text(
            "✅ SFP модули обновлены!\n\n"
            f"👤 Сотрудник: {emp.get('full_name', emp_id)}\n"
            f"🧿 Модель: {module_name}\n"
            f"{'➕ Добавлено' if action == 'add' else '➖ Списано'}: {quantity} шт.\n"
            f"📊 Всего: {total} шт.",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text("❌ Не удалось выполнить операцию.")

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


def _sfp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="sfp_confirm")],
            [InlineKeyboardButton("✏️ Изменить количество", callback_data="sfp_edit")],
            [InlineKeyboardButton("📝 Добавить комментарий", callback_data="sfp_comment")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
    )


def _sfp_confirmation_text(employee_name: str, module_name: str, quantity: int, action: str, comment: str) -> str:
    sign = "+" if action == "add" else "-"
    action_word = "добавление" if action == "add" else "списание"
    comment_text = comment or "—"
    return (
        "Проверьте данные и подтвердите операцию:\n\n"
        f"👤 Сотрудник: <b>{employee_name}</b>\n"
        f"🧿 SFP модуль: {module_name}\n"
        f"Действие: {action_word}\n"
        f"Количество: {sign}{quantity} шт.\n"
        f"📝 Комментарий: {comment_text}"
    )


async def show_sfp_confirmation(message, employee: dict, module_name: str, action: str, quantity: int, context: ContextTypes.DEFAULT_TYPE):
    text = _sfp_confirmation_text(
        employee.get("full_name", "—") if employee else "—",
        module_name,
        quantity,
        action,
        context.user_data.get("sfp_comment", ""),
    )
    await message.reply_text(
        text,
        reply_markup=_sfp_keyboard(),
        parse_mode="HTML",
    )
    return CONFIRM_SFP_OPERATION
