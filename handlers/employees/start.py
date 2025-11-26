"""
Стартовые обработчики управления сотрудниками
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    MANAGE_ACTION,
    ADD_EMPLOYEE_NAME,
    DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL,
    SELECT_MATERIAL_ACTION,
    SELECT_EMPLOYEE_FOR_ROUTER,
    SELECT_EMPLOYEE_FOR_SNR,
    SELECT_EMPLOYEE_FOR_ONU,
    SELECT_EMPLOYEE_FOR_MEDIA,
    logger,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread

ENTRY_MODE_KEY = "manage_entry_mode"
ENTRY_MODE_EMPLOYEES = "employees"
ENTRY_MODE_RESOURCES = "resources"


async def manage_employees_start(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с управлением сотрудниками"""
    user_id = update.effective_user.id

    if not flow.admin_manager or not flow.admin_manager.is_admin(user_id):
        text = "⛔ У вас нет прав для управления сотрудниками."
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END

    context.user_data[ENTRY_MODE_KEY] = ENTRY_MODE_EMPLOYEES

    keyboard = [
        [InlineKeyboardButton("➕ Добавить сотрудника", callback_data="manage_add")],
        [InlineKeyboardButton("➖ Удалить сотрудника", callback_data="manage_delete")],
        [InlineKeyboardButton("🔐 Управление доступом", callback_data="manage_access")],
        [InlineKeyboardButton("👑 Управление администраторами", callback_data="manage_admins")],
        [InlineKeyboardButton("👤 Список всех сотрудников", callback_data="manage_list")],
        [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "👥 <b>Управление сотрудниками</b>\n\nВыберите действие:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    return MANAGE_ACTION


async def manage_resources_start(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отдельное меню материалов и оборудования"""
    user_id = update.effective_user.id

    if not flow.admin_manager or not flow.admin_manager.is_admin(user_id):
        text = "⛔ У вас нет прав для управления материалами и оборудованием."
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END

    context.user_data[ENTRY_MODE_KEY] = ENTRY_MODE_RESOURCES

    keyboard = [
        [InlineKeyboardButton("📦 Управление материалами", callback_data="manage_materials")],
        [InlineKeyboardButton("📡 Управление роутерами", callback_data="manage_routers")],
        [InlineKeyboardButton("🧰 SNR Оптические боксы", callback_data="manage_snr")],
        [InlineKeyboardButton("🔌 ONU абон.терминалы", callback_data="manage_onu")],
        [InlineKeyboardButton("🔄 Медиаконверторы", callback_data="manage_media")],
        [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "📦 <b>Материалы и оборудование</b>\n\nВыберите раздел:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    return MANAGE_ACTION


async def manage_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбранного действия"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "manage_cancel":
        context.user_data.pop(ENTRY_MODE_KEY, None)
        await query.edit_message_text("❌ Управление сотрудниками отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "back_to_manage":
        return await return_to_manage_menu(flow, update, context)

    if data == "manage_add":
        await query.edit_message_text(
            "➕ <b>Добавление сотрудника</b>\n\nВведите ФИО сотрудника:",
            parse_mode="HTML",
        )
        return ADD_EMPLOYEE_NAME

    if data == "manage_delete":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников для удаления.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(f"🗑 {emp['full_name']}", callback_data=f"del_emp_{emp['id']}")]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="delete_cancel")])

        await query.edit_message_text(
            "➖ <b>Удаление сотрудника</b>\n\nВыберите сотрудника для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return DELETE_EMPLOYEE_SELECT

    if data == "manage_materials":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = []
        for emp in employees:
            fiber = emp.get("fiber_balance", 0) or 0
            twisted = emp.get("twisted_pair_balance", 0) or 0
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📦 {emp['full_name']} (ВОЛС: {fiber}м, ВП: {twisted}м)",
                        callback_data=f"mat_emp_{emp['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "📦 <b>Управление материалами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL

    if data == "manage_routers":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = []
        for emp in employees:
            routers = await run_in_thread(flow.db.get_employee_routers, emp["id"])
            router_count = sum(r["quantity"] for r in routers)
            router_text = f"{router_count} шт." if router_count > 0 else "нет"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📡 {emp['full_name']} ({router_text})",
                        callback_data=f"rtr_emp_{emp['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "📡 <b>Управление роутерами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_ROUTER
    
    if data == "manage_snr":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        
        keyboard = []
        for emp in employees:
            boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp["id"])
            total = sum(box["quantity"] for box in boxes)
            info = f"{total} шт." if total > 0 else "нет"
            keyboard.append(
                [InlineKeyboardButton(f"🧰 {emp['full_name']} ({info})", callback_data=f"snr_emp_{emp['id']}")]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])
        
        await query.edit_message_text(
            "🧰 <b>SNR Оптические боксы</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_SNR

    if data == "manage_onu":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(
                    f"🔌 {emp['full_name']} (ONU: {sum(box['quantity'] for box in (await run_in_thread(flow.db.get_employee_onu, emp['id'])) or [])} шт.)",
                    callback_data=f"onu_emp_{emp['id']}"
                )
            ]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "🔌 <b>ONU абон.терминалы</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_ONU

    if data == "manage_media":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = [
            [
                InlineKeyboardButton(
                    f"🔄 {emp['full_name']} (МК: {sum(dev['quantity'] for dev in (await run_in_thread(flow.db.get_employee_media_converters, emp['id'])) or [])} шт.)",
                    callback_data=f"media_emp_{emp['id']}"
                )
            ]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "🔄 <b>Медиаконверторы</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_MEDIA

    if data == "manage_access":
        if not flow.access_manager:
            await query.answer("Функция недоступна", show_alert=True)
            return MANAGE_ACTION
        return await flow.access_menu(update, context)

    if data == "manage_admins":
        if not flow.admin_manager:
            await query.answer("Функция недоступна", show_alert=True)
            return MANAGE_ACTION
        return await flow.admin_menu(update, context)

    if data == "manage_list":
        employees = await run_in_thread(flow.db.get_all_employees)
        if not employees:
            text = "👤 <b>Список всех сотрудников</b>\n\nСписок пуст."
        else:
            lines = []
            for idx, emp in enumerate(employees, 1):
                lines.append(f"{idx}. {emp['full_name']}")
            text = f"👤 <b>Список всех сотрудников ({len(employees)}):</b>\n\n" + "\n\n".join(lines)

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return MANAGE_ACTION

    logger.warning("Необработанное действие управления сотрудниками: %s", data)
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def return_to_manage_menu(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Вернуться к актуальному меню (сотрудники или ресурсы)"""
    mode = context.user_data.get(ENTRY_MODE_KEY, ENTRY_MODE_EMPLOYEES)
    if mode == ENTRY_MODE_RESOURCES:
        return await manage_resources_start(flow, update, context)
    return await manage_employees_start(flow, update, context)

