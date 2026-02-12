"""
Вспомогательные обработчики отображения списков
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from utils.keyboards import get_main_keyboard


async def show_employees_list(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит список сотрудников с материалами и роутерами"""
    employees = flow.db.get_all_employees()

<<<<<<< Updated upstream
    if not employees:
=======
    included = []
    for emp in employees:
        fiber_balance = emp.get("fiber_balance", 0) or 0
        twisted_external_balance = emp.get("twisted_pair_external_balance", 0) or 0
        twisted_internal_balance = emp.get("twisted_pair_internal_balance", 0) or 0
        twisted_balance = twisted_external_balance + twisted_internal_balance
        routers = await run_in_thread(flow.db.get_employee_routers, emp["id"])
        router_count = sum(r["quantity"] for r in routers)
        snr_boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp["id"])
        snr_count = sum(box["quantity"] for box in snr_boxes)
        onu_devices = await run_in_thread(flow.db.get_employee_onu, emp["id"])
        onu_count = sum(dev["quantity"] for dev in onu_devices or [])
        media_devices = await run_in_thread(flow.db.get_employee_media_converters, emp["id"])
        media_count = sum(dev["quantity"] for dev in media_devices or [])
        sfp_modules = await run_in_thread(flow.db.get_employee_sfp_modules, emp["id"])
        sfp_count = sum(mod["quantity"] for mod in sfp_modules or [])

        if (
            fiber_balance > 0
            or twisted_balance > 0
            or router_count > 0
            or snr_count > 0
            or onu_count > 0
            or media_count > 0
        ):
            included.append(
                (
                    emp,
                    fiber_balance,
                    twisted_balance,
                    twisted_external_balance,
                    twisted_internal_balance,
                    routers,
                    router_count,
                    snr_boxes,
                    snr_count,
                    onu_devices or [],
                    onu_count,
                    media_devices or [],
                    media_count,
                    sfp_modules or [],
                    sfp_count,
                )
            )

    if not included:
>>>>>>> Stashed changes
        await update.message.reply_text(
            "📋 <b>Список сотрудников пуст</b>\n\n"
            "Добавьте сотрудников через меню\n"
            "👥 Управление сотрудниками → ➕ Добавить сотрудника",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    message_lines = ["👤 <b>Список сотрудников</b>\n"]

    for idx, emp in enumerate(employees, 1):
        fiber_balance = emp.get("fiber_balance", 0) or 0
        twisted_balance = emp.get("twisted_pair_balance", 0) or 0
        routers = flow.db.get_employee_routers(emp["id"])
        router_count = sum(r["quantity"] for r in routers)

<<<<<<< Updated upstream
=======
    for idx, (
        emp,
        fiber_balance,
        twisted_balance,
        twisted_external_balance,
        twisted_internal_balance,
        routers,
        router_count,
        snr_boxes,
        snr_count,
        onu_devices,
        onu_count,
        media_devices,
        media_count,
        sfp_modules,
        sfp_count,
    ) in enumerate(included, 1):
>>>>>>> Stashed changes
        message_lines.append(f"{idx}. <b>{emp['full_name']}</b>")
        message_lines.append("   📦 Материалы:")
        message_lines.append(f"   • ВОЛС: {fiber_balance} м")
        message_lines.append(f"   • Витая пара (общая): {twisted_balance} м")
        message_lines.append(f"   • Внеш. витая пара: {twisted_external_balance} м")
        message_lines.append(f"   • Внут. витая пара: {twisted_internal_balance} м")
        message_lines.append(f"   📡 Роутеры: {router_count} шт.")

        if routers:
            message_lines.append("   Модели:")
            for router in routers:
                message_lines.append(
                    f"   • {router['router_name']}: {router['quantity']} шт."
                )
        message_lines.append("")

    message_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    message_lines.append(f"<b>Всего сотрудников:</b> {len(employees)}")

    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )


