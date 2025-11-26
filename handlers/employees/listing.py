"""
Вспомогательные обработчики отображения списков
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread


async def show_employees_list(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит список сотрудников с материалами и роутерами"""
    employees = await run_in_thread(flow.db.get_all_employees)

    included = []
    for emp in employees:
        fiber_balance = emp.get("fiber_balance", 0) or 0
        twisted_balance = emp.get("twisted_pair_balance", 0) or 0
        routers = await run_in_thread(flow.db.get_employee_routers, emp["id"])
        router_count = sum(r["quantity"] for r in routers)
        snr_boxes = await run_in_thread(flow.db.get_employee_snr_boxes, emp["id"])
        snr_count = sum(box["quantity"] for box in snr_boxes)
        onu_devices = await run_in_thread(flow.db.get_employee_onu, emp["id"])
        onu_count = sum(dev["quantity"] for dev in onu_devices or [])
        media_devices = await run_in_thread(flow.db.get_employee_media_converters, emp["id"])
        media_count = sum(dev["quantity"] for dev in media_devices or [])

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
                    routers,
                    router_count,
                    snr_boxes,
                    snr_count,
                    onu_devices or [],
                    onu_count,
                    media_devices or [],
                    media_count,
                )
            )

    if not included:
        await update.message.reply_text(
            "📋 <b>Список сотрудников МОЛ пуст</b>\n\n"
            "Нет сотрудников с материалами или оборудованием.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    message_lines = ["📋 <b>Список сотрудников МОЛ</b>\n"]

    for idx, (
        emp,
        fiber_balance,
        twisted_balance,
        routers,
        router_count,
        snr_boxes,
        snr_count,
        onu_devices,
        onu_count,
        media_devices,
        media_count,
    ) in enumerate(included, 1):
        message_lines.append(f"{idx}. <b>{emp['full_name']}</b>")
        message_lines.append("   📦 Материалы:")
        message_lines.append(f"   • ВОЛС: {fiber_balance} м")
        message_lines.append(f"   • Витая пара: {twisted_balance} м")
        message_lines.append(f"   📡 Роутеры: {router_count} шт.")

        if routers:
            message_lines.append("   Модели:")
            for router in routers:
                message_lines.append(
                    f"   • {router['router_name']}: {router['quantity']} шт."
                )
        message_lines.append(f"🧰 SNR боксы: {snr_count} шт.")
        message_lines.append(f"🔌 ONU: {onu_count} шт.")
        message_lines.append(f"🔄 Медиаконверторы: {media_count} шт.")
        message_lines.append("")

    message_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    message_lines.append(f"<b>Всего сотрудников:</b> {len(included)}")

    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )
