"""
Обработка комментариев для операций с материалами и оборудованием
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    CONFIRM_MATERIAL_OPERATION,
    CONFIRM_ROUTER_OPERATION,
    CONFIRM_SNR_OPERATION,
    CONFIRM_ONU_OPERATION,
    CONFIRM_MEDIA_OPERATION,
)
from utils.helpers import run_in_thread
from utils.keyboards import get_main_keyboard

from . import materials, routers, snr_boxes, onu, media_converters, sfp_modules


async def enter_operation_comment(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранить комментарий и вернуть на подтверждение операции"""
    comment = (update.message.text or "").strip()
    if not comment:
        comment = "-"

    target = context.user_data.get("comment_target")
    if not target:
        await update.message.reply_text("⚠️ Не удалось определить операцию для комментария.", reply_markup=get_main_keyboard())
        context.user_data.pop("comment_target", None)
        return ConversationHandler.END

    context.user_data.pop("comment_target", None)

    if target == "material":
        context.user_data["material_comment"] = comment
        emp_id = context.user_data.get("selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        action = context.user_data.get("material_action", "add")
        return await materials.show_material_confirmation(flow, update.message, context, employee, action)

    if target == "router":
        context.user_data["router_comment"] = comment
        emp_id = context.user_data.get("selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        router_name = context.user_data.get("router_name", "-")
        action = context.user_data.get("router_action", "add")
        quantity = context.user_data.get("router_quantity", 0)
        return await routers.show_router_confirmation(update.message, employee, router_name, action, quantity, context)

    if target == "snr":
        context.user_data["snr_comment"] = comment
        emp_id = context.user_data.get("snr_selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        box_name = context.user_data.get("snr_box_name", "-")
        action = context.user_data.get("snr_action", "add")
        quantity = context.user_data.get("snr_box_quantity", 0)
        return await snr_boxes.show_snr_confirmation(update.message, employee, box_name, action, quantity, context)

    if target == "onu":
        context.user_data["onu_comment"] = comment
        emp_id = context.user_data.get("selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        device_name = context.user_data.get("onu_name", "-")
        action = context.user_data.get("onu_action", "add")
        quantity = context.user_data.get("onu_quantity", 0)
        return await onu.show_onu_confirmation(update.message, employee, device_name, action, quantity, context)

    if target == "media":
        context.user_data["media_comment"] = comment
        emp_id = context.user_data.get("selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        device_name = context.user_data.get("media_name", "-")
        action = context.user_data.get("media_action", "add")
        quantity = context.user_data.get("media_quantity", 0)
        return await media_converters.show_media_confirmation(update.message, employee, device_name, action, quantity, context)

    if target == "sfp":
        context.user_data["sfp_comment"] = comment
        emp_id = context.user_data.get("selected_employee_id")
        employee = await run_in_thread(flow.db.get_employee_by_id, emp_id) if emp_id else {}
        module_name = context.user_data.get("sfp_name", "-")
        action = context.user_data.get("sfp_action", "add")
        quantity = context.user_data.get("sfp_quantity", 0)
        return await sfp_modules.show_sfp_confirmation(update.message, employee, module_name, action, quantity, context)

    await update.message.reply_text("⚠️ Неизвестный тип операции для комментария.", reply_markup=get_main_keyboard())
    return ConversationHandler.END
