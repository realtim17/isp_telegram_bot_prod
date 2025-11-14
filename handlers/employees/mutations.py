"""
Добавление и удаление сотрудников (модульная версия)
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import get_main_keyboard
from config import ADD_EMPLOYEE_NAME, CONFIRM_ADD_EMPLOYEE, DELETE_EMPLOYEE_SELECT


async def add_employee_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ввод ФИО и запрос подтверждения"""
    full_name = update.message.text.strip()

    if len(full_name) < 3:
        await update.message.reply_text(
            "⚠️ ФИО должно содержать минимум 3 символа. Попробуйте еще раз:"
        )
        return ADD_EMPLOYEE_NAME

    context.user_data["pending_employee_name"] = full_name

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_add_employee")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="edit_add_employee")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
    )

    await update.message.reply_text(
        f"Вы ввели ФИО: <b>{full_name}</b>\n\nПодтвердить добавление?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return CONFIRM_ADD_EMPLOYEE


async def confirm_add_employee(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение/отмена добавления сотрудника"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "manage_cancel":
        context.user_data.pop("pending_employee_name", None)
        await query.edit_message_text("❌ Добавление сотрудника отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "edit_add_employee":
        await query.edit_message_text(
            "✏️ <b>Добавление сотрудника</b>\n\nВведите ФИО сотрудника:",
            parse_mode="HTML",
        )
        return ADD_EMPLOYEE_NAME

    if data != "confirm_add_employee":
        return CONFIRM_ADD_EMPLOYEE

    full_name = context.user_data.get("pending_employee_name")
    if not full_name:
        await query.edit_message_text("❌ Не найдено ФИО. Попробуйте снова.")
        return ADD_EMPLOYEE_NAME

    employee_id = flow.db.add_employee(full_name)
    if employee_id:
        await query.edit_message_text(
            f"✅ Сотрудник <b>{full_name}</b> успешно добавлен!",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            f"⚠️ Сотрудник <b>{full_name}</b> уже существует в системе!",
            parse_mode="HTML",
        )

    context.user_data.pop("pending_employee_name", None)
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def delete_employee_confirm(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление сотрудника с подтверждением"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "delete_cancel":
        await query.edit_message_text("❌ Удаление отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data.startswith("confirm_delete_"):
        emp_id = int(data.split("_")[-1])
        employee = flow.db.get_employee_by_id(emp_id)
        if employee and flow.db.delete_employee(emp_id):
            await query.edit_message_text(
                f"✅ Сотрудник <b>{employee['full_name']}</b> удален!",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text("❌ Ошибка при удалении сотрудника.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data.startswith("del_emp_"):
        emp_id = int(data.split("_")[2])
        employee = flow.db.get_employee_by_id(emp_id)
        if not employee:
            await query.edit_message_text("❌ Сотрудник не найден.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Подтвердить удаление", callback_data=f"confirm_delete_{emp_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="delete_cancel")],
            ]
        )
        await query.edit_message_text(
            f"Удалить сотрудника <b>{employee['full_name']}</b>?",
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return DELETE_EMPLOYEE_SELECT

    return DELETE_EMPLOYEE_SELECT
