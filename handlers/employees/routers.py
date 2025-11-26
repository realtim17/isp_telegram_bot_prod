"""
Обработчики управления роутерами сотрудников (модульная версия)
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_ROUTER,
    SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME,
    ENTER_ROUTER_QUANTITY,
    CONFIRM_ROUTER_OPERATION,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread


async def select_employee_for_router(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Выбор сотрудника для операций с роутерами"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import return_to_manage_menu

        return await return_to_manage_menu(flow, update, context)

    emp_id = int(query.data.split("_")[-1])
    context.user_data["selected_employee_id"] = emp_id

    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    routers = await run_in_thread(flow.db.get_employee_routers, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    router_text = ""
    if routers:
        for router in routers:
            router_text += f"  • {router['router_name']}: {router['quantity']} шт.\n"
    else:
        router_text = "  Роутеров нет\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить роутеры", callback_data="rtr_action_add")],
        [InlineKeyboardButton("➖ Списать роутер", callback_data="rtr_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="rtr_back_to_list")],
    ]

    await query.edit_message_text(
        "📡 <b>Роутеры сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущие роутеры:\n{router_text}\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ROUTER_ACTION


async def select_router_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор операции над роутером"""
    query = update.callback_query
    await query.answer()

    if query.data == "rtr_back_to_list":
        employees = await run_in_thread(flow.db.get_all_employees)
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

    action = query.data.split("_")[-1]
    context.user_data["router_action"] = action

    if action == "add":
        keyboard = [
            [InlineKeyboardButton("📡 SNR AX 2", callback_data="router_model_SNR AX 2")],
            [InlineKeyboardButton("📡 TP-Link AX 12", callback_data="router_model_TP-Link AX 12")],
            [InlineKeyboardButton("📡 Keenetic Speedster", callback_data="router_model_Keenetic Speedster")],
            [InlineKeyboardButton("✏️ Ввести вручную", callback_data="router_model_manual")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
        await query.edit_message_text(
            "➕ <b>Добавление роутеров</b>\n\nВыберите модель роутера или введите свою:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return ENTER_ROUTER_NAME

    emp_id = context.user_data.get("selected_employee_id")
    routers = await run_in_thread(flow.db.get_employee_routers, emp_id)
    if not routers:
        await query.edit_message_text("⚠️ У сотрудника нет роутеров для списания.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(
                f"{router['router_name']} ({router['quantity']} шт.)",
                callback_data=f"deduct_router_{router['id']}",
            )
        ]
        for router in routers
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

    await query.edit_message_text(
        "➖ <b>Списание роутера</b>\n\nВыберите роутер для списания:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ROUTER_ACTION


async def enter_router_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение модели роутера или переход к списанию"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.data.startswith("router_model_"):
            if query.data == "router_model_manual":
                await query.edit_message_text(
                    "➕ <b>Добавление роутеров</b>\n\nВведите название роутера:",
                    parse_mode="HTML",
                )
                return ENTER_ROUTER_NAME

            router_name = query.data.replace("router_model_", "")
            context.user_data["router_name"] = router_name
            await query.edit_message_text(
                f"➕ <b>Добавление роутеров</b>\n\nМодель: {router_name}\n\nВведите количество роутеров:",
                parse_mode="HTML",
            )
            return ENTER_ROUTER_QUANTITY

        router_id = int(query.data.split("_")[-1])
        emp_id = context.user_data.get("selected_employee_id")
        routers = await run_in_thread(flow.db.get_employee_routers, emp_id)
        selected_router = next((r for r in routers if r["id"] == router_id), None)

        if not selected_router:
            await query.edit_message_text("❌ Роутер не найден.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END

        context.user_data["router_name"] = selected_router["router_name"]
        context.user_data["router_action"] = "deduct"

        await query.edit_message_text(
            "➖ <b>Списание роутера</b>\n\n"
            f"📡 Роутер: {selected_router['router_name']}\n"
            f"📊 Доступно: {selected_router['quantity']} шт.\n\n"
            "Введите количество для списания (целое число):",
            parse_mode="HTML",
        )
        return ENTER_ROUTER_QUANTITY

    router_name = update.message.text.strip()
    context.user_data["router_name"] = router_name
    await update.message.reply_text(
        f"✅ Роутер: {router_name}\n\nВведите количество (целое число):",
        parse_mode="HTML",
    )
    return ENTER_ROUTER_QUANTITY


async def enter_router_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение количества роутеров и запрос подтверждения"""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число (например: 5)"
        )
        return ENTER_ROUTER_QUANTITY

    context.user_data["router_quantity"] = quantity
    emp_id = context.user_data.get("selected_employee_id")
    router_name = context.user_data.get("router_name")
    action = context.user_data.get("router_action")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    symbol = "+" if action == "add" else "-"

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="router_confirm")],
            [InlineKeyboardButton("✏️ Изменить", callback_data="router_edit")],
            [InlineKeyboardButton("❌ Отмена", callback_data="router_cancel")],
        ]
    )

    await update.message.reply_text(
        f"👤 Сотрудник: <b>{employee['full_name']}</b>\n"
        f"📡 Роутер: {router_name}\n"
        f"Количество: {symbol}{quantity} шт.\n\n"
        "Подтвердить операцию?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return CONFIRM_ROUTER_OPERATION


async def confirm_router_operation(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Подтверждение операций с роутерами"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "router_cancel":
        context.user_data.clear()
        await query.edit_message_text("❌ Операция с роутерами отменена.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "router_edit":
        await query.edit_message_text(
            "✏️ Введите количество роутеров заново:",
            parse_mode="HTML",
        )
        context.user_data.pop("router_quantity", None)
        return ENTER_ROUTER_QUANTITY

    if data != "router_confirm":
        return CONFIRM_ROUTER_OPERATION

    emp_id = context.user_data.get("selected_employee_id")
    router_name = context.user_data.get("router_name")
    quantity = context.user_data.get("router_quantity", 0)
    action = context.user_data.get("router_action")
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)

    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        context.user_data.clear()
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    created_by = query.from_user.id if query and query.from_user else None

    if action == "add":
        success = await run_in_thread(
            flow.db.add_router_to_employee, emp_id, router_name, quantity, created_by
        )
        if success:
            new_quantity = await run_in_thread(flow.db.get_router_quantity, emp_id, router_name)
            await query.edit_message_text(
                "✅ <b>Роутеры добавлены!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"📡 Роутер: {router_name}\n"
                f"➕ Добавлено: {quantity} шт.\n"
                f"📊 Всего: {new_quantity} шт.",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text("❌ Ошибка при добавлении роутеров.")
    else:
        success = await run_in_thread(
            flow.db.deduct_router_from_employee,
            emp_id,
            router_name,
            quantity,
            None,
            created_by,
        )
        if success:
            new_quantity = await run_in_thread(flow.db.get_router_quantity, emp_id, router_name)
            await query.edit_message_text(
                "✅ <b>Роутеры списаны!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"📡 Роутер: {router_name}\n"
                f"➖ Списано: {quantity} шт.\n"
                f"📊 Осталось: {new_quantity} шт.",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при списании роутеров (недостаточно в наличии).",
                parse_mode="HTML",
            )

    context.user_data.clear()
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


