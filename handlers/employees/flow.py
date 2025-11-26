"""
Класс-координатор управления сотрудниками
"""
from __future__ import annotations

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from config import (
    MANAGE_ACTION,
    ADD_EMPLOYEE_NAME,
    CONFIRM_ADD_EMPLOYEE,
    DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL,
    SELECT_MATERIAL_ACTION,
    ENTER_FIBER_AMOUNT,
    ENTER_TWISTED_AMOUNT,
    CONFIRM_MATERIAL_OPERATION,
    SELECT_EMPLOYEE_FOR_ROUTER,
    SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME,
    ENTER_ROUTER_QUANTITY,
    CONFIRM_ROUTER_OPERATION,
    SELECT_EMPLOYEE_FOR_SNR,
    SELECT_SNR_ACTION,
    ENTER_SNR_NAME,
    ENTER_SNR_QUANTITY,
    CONFIRM_SNR_OPERATION,
    MANAGE_ACCESS,
    ENTER_ACCESS_ID,
    MANAGE_ADMINS,
    ENTER_ADMIN_ID,
    SELECT_EMPLOYEE_FOR_ONU,
    SELECT_ONU_ACTION,
    ENTER_ONU_NAME,
    ENTER_ONU_QUANTITY,
    CONFIRM_ONU_OPERATION,
    SELECT_EMPLOYEE_FOR_MEDIA,
    SELECT_MEDIA_ACTION,
    ENTER_MEDIA_NAME,
    ENTER_MEDIA_QUANTITY,
    CONFIRM_MEDIA_OPERATION,
)
from database import Database

from . import (
    listing,
    materials,
    mutations,
    routers,
    snr_boxes,
    start,
    access_control,
    admin_control,
    onu,
    media_converters,
)


class EmployeeFlow:
    """Инкапсулирует логику управления сотрудниками"""

    def __init__(self, db: Database, access_manager=None, admin_manager=None) -> None:
        self.db = db
        self.access_manager = access_manager
        self.admin_manager = admin_manager

    # --- Основные действия ---
    async def manage_employees_start(self, update, context):
        return await start.manage_employees_start(self, update, context)

    async def manage_resources_start(self, update, context):
        return await start.manage_resources_start(self, update, context)

    async def manage_action(self, update, context):
        return await start.manage_action(self, update, context)

    async def add_employee_name(self, update, context):
        return await mutations.add_employee_name(self, update, context)

    async def confirm_add_employee(self, update, context):
        return await mutations.confirm_add_employee(self, update, context)

    async def delete_employee_confirm(self, update, context):
        return await mutations.delete_employee_confirm(self, update, context)

    # --- Материалы ---
    async def select_employee_for_material(self, update, context):
        return await materials.select_employee_for_material(self, update, context)

    async def select_material_action(self, update, context):
        return await materials.select_material_action(self, update, context)

    async def enter_fiber_amount(self, update, context):
        return await materials.enter_fiber_amount(self, update, context)

    async def enter_twisted_amount(self, update, context):
        return await materials.enter_twisted_amount(self, update, context)

    async def confirm_material_operation(self, update, context):
        return await materials.confirm_material_operation(self, update, context)

    # --- Роутеры ---
    async def select_employee_for_router(self, update, context):
        return await routers.select_employee_for_router(self, update, context)

    async def select_router_action(self, update, context):
        return await routers.select_router_action(self, update, context)

    async def enter_router_name(self, update, context):
        return await routers.enter_router_name(self, update, context)

    async def enter_router_quantity(self, update, context):
        return await routers.enter_router_quantity(self, update, context)

    async def confirm_router_operation(self, update, context):
        return await routers.confirm_router_operation(self, update, context)

    # --- SNR боксы ---
    async def select_employee_for_snr(self, update, context):
        return await snr_boxes.select_employee_for_snr(self, update, context)

    async def select_snr_action(self, update, context):
        return await snr_boxes.select_snr_action(self, update, context)

    async def enter_snr_name(self, update, context):
        return await snr_boxes.enter_snr_name(self, update, context)

    async def enter_snr_quantity(self, update, context):
        return await snr_boxes.enter_snr_quantity(self, update, context)

    async def confirm_snr_operation(self, update, context):
        return await snr_boxes.confirm_snr_operation(self, update, context)

    # --- ONU ---
    async def select_employee_for_onu(self, update, context):
        return await onu.select_employee_for_onu(self, update, context)

    async def select_onu_action(self, update, context):
        return await onu.select_onu_action(self, update, context)

    async def enter_onu_name(self, update, context):
        return await onu.enter_onu_name(self, update, context)

    async def enter_onu_quantity(self, update, context):
        return await onu.enter_onu_quantity(self, update, context)

    async def confirm_onu_operation(self, update, context):
        return await onu.confirm_onu_operation(self, update, context)

    # --- Медиаконверторы ---
    async def select_employee_for_media(self, update, context):
        return await media_converters.select_employee_for_media(self, update, context)

    async def select_media_action(self, update, context):
        return await media_converters.select_media_action(self, update, context)

    async def enter_media_name(self, update, context):
        return await media_converters.enter_media_name(self, update, context)

    async def enter_media_quantity(self, update, context):
        return await media_converters.enter_media_quantity(self, update, context)

    async def confirm_media_operation(self, update, context):
        return await media_converters.confirm_media_operation(self, update, context)

    # --- Управление доступом ---
    async def access_menu(self, update, context):
        return await access_control.show_access_menu(self, update, context)

    async def access_action(self, update, context):
        return await access_control.handle_access_action(self, update, context)

    async def enter_access_id(self, update, context):
        return await access_control.enter_access_user_id(self, update, context)

    # --- Управление администраторами ---
    async def admin_menu(self, update, context):
        return await admin_control.show_admin_menu(self, update, context)

    async def admin_action(self, update, context):
        return await admin_control.handle_admin_action(self, update, context)

    async def enter_admin_id(self, update, context):
        return await admin_control.enter_admin_user_id(self, update, context)

    # --- Общий список ---
    async def show_employees_list(self, update, context):
        return await listing.show_employees_list(self, update, context)

    # --- Построение ConversationHandler ---
    def build_conversation(self, text_input_filter, fallbacks) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler('manage_employees', self.manage_employees_start),
                MessageHandler(filters.Regex("^👥 Управление сотрудниками$"), self.manage_employees_start),
                MessageHandler(filters.Regex("^📦 Материалы и оборудование$"), self.manage_resources_start),
            ],
            states={
                MANAGE_ACTION: [
                    CallbackQueryHandler(self.manage_action, pattern="^(manage_|back_to_manage)")
                ],
                ADD_EMPLOYEE_NAME: [
                    MessageHandler(text_input_filter, self.add_employee_name)
                ],
                CONFIRM_ADD_EMPLOYEE: [
                    CallbackQueryHandler(
                        self.confirm_add_employee,
                        pattern="^(confirm_add_employee|edit_add_employee|manage_cancel)",
                    )
                ],
                DELETE_EMPLOYEE_SELECT: [
                    CallbackQueryHandler(
                        self.delete_employee_confirm,
                        pattern="^(del_emp_|delete_cancel|confirm_delete_)",
                    )
                ],
                SELECT_EMPLOYEE_FOR_MATERIAL: [
                    CallbackQueryHandler(
                        self.select_employee_for_material, pattern="^(mat_emp_|back_to_manage)"
                    )
                ],
                SELECT_MATERIAL_ACTION: [
                    CallbackQueryHandler(
                        self.select_material_action, pattern="^(mat_action_|mat_back_to_list)"
                    )
                ],
                ENTER_FIBER_AMOUNT: [
                    MessageHandler(text_input_filter, self.enter_fiber_amount)
                ],
                ENTER_TWISTED_AMOUNT: [
                    MessageHandler(text_input_filter, self.enter_twisted_amount)
                ],
                CONFIRM_MATERIAL_OPERATION: [
                    CallbackQueryHandler(
                        self.confirm_material_operation,
                        pattern="^(material_confirm|material_edit|material_cancel)",
                    )
                ],
                SELECT_EMPLOYEE_FOR_ROUTER: [
                    CallbackQueryHandler(
                        self.select_employee_for_router, pattern="^(rtr_emp_|back_to_manage)"
                    )
                ],
                SELECT_ROUTER_ACTION: [
                    CallbackQueryHandler(
                        self.select_router_action, pattern="^(rtr_action_|rtr_back_to_list)"
                    ),
                    CallbackQueryHandler(
                        self.enter_router_name, pattern="^(deduct_router_|router_model_)"
                    ),
                ],
                ENTER_ROUTER_NAME: [
                    CallbackQueryHandler(self.enter_router_name, pattern="^router_model_"),
                    MessageHandler(text_input_filter, self.enter_router_name),
                ],
                ENTER_ROUTER_QUANTITY: [
                    MessageHandler(text_input_filter, self.enter_router_quantity)
                ],
                CONFIRM_ROUTER_OPERATION: [
                    CallbackQueryHandler(
                        self.confirm_router_operation,
                        pattern="^(router_confirm|router_edit|router_cancel)",
                    )
                ],
                SELECT_EMPLOYEE_FOR_SNR: [
                    CallbackQueryHandler(
                        self.select_employee_for_snr, pattern="^(snr_emp_|back_to_manage)"
                    )
                ],
                SELECT_SNR_ACTION: [
                    CallbackQueryHandler(
                        self.select_snr_action,
                        pattern="^(snr_action_|snr_back_to_list)"
                    )
                ],
                ENTER_SNR_NAME: [
                    CallbackQueryHandler(
                        self.enter_snr_name,
                        pattern="^(snr_model_|snr_model_manual|manage_cancel)"
                    ),
                    MessageHandler(text_input_filter, self.enter_snr_name),
                ],
                ENTER_SNR_QUANTITY: [
                    MessageHandler(text_input_filter, self.enter_snr_quantity)
                ],
                CONFIRM_SNR_OPERATION: [
                    CallbackQueryHandler(
                        self.confirm_snr_operation,
                        pattern="^(snr_confirm|snr_edit|snr_cancel)"
                    )
                ],
                MANAGE_ACCESS: [
                    CallbackQueryHandler(
                        self.access_action,
                        pattern="^(access_|revoke_access_|back_to_manage)"
                    )
                ],
                ENTER_ACCESS_ID: [
                    MessageHandler(text_input_filter, self.enter_access_id),
                    CallbackQueryHandler(
                        self.access_action,
                        pattern="^(access_back_to_menu|back_to_manage)"
                    )
                ],
                MANAGE_ADMINS: [
                    CallbackQueryHandler(
                        self.admin_action,
                        pattern="^(admin_|revoke_admin_|back_to_manage)"
                    )
                ],
                ENTER_ADMIN_ID: [
                    MessageHandler(text_input_filter, self.enter_admin_id),
                    CallbackQueryHandler(
                        self.admin_action,
                        pattern="^(admin_back_to_menu|back_to_manage)"
                    )
                ],
                SELECT_EMPLOYEE_FOR_ONU: [
                    CallbackQueryHandler(
                        self.select_employee_for_onu, pattern="^(onu_emp_|back_to_manage)"
                    )
                ],
                SELECT_ONU_ACTION: [
                    CallbackQueryHandler(
                        self.select_onu_action, pattern="^(onu_action_.*|onu_back_to_list|manage_cancel)$"
                    ),
                    CallbackQueryHandler(
                        self.enter_onu_name, pattern="^onu_model_.*"
                    ),
                ],
                ENTER_ONU_NAME: [
                    CallbackQueryHandler(self.enter_onu_name, pattern="^(onu_model_.*|manage_cancel)$"),
                    MessageHandler(text_input_filter, self.enter_onu_name),
                ],
                ENTER_ONU_QUANTITY: [
                    MessageHandler(text_input_filter, self.enter_onu_quantity)
                ],
                CONFIRM_ONU_OPERATION: [
                    CallbackQueryHandler(
                        self.confirm_onu_operation,
                        pattern="^(onu_confirm|onu_edit|manage_cancel)"
                    )
                ],
                SELECT_EMPLOYEE_FOR_MEDIA: [
                    CallbackQueryHandler(
                        self.select_employee_for_media, pattern="^(media_emp_|back_to_manage)"
                    )
                ],
                SELECT_MEDIA_ACTION: [
                    CallbackQueryHandler(
                        self.select_media_action, pattern="^(media_action_.*|media_back_to_list|manage_cancel)$"
                    ),
                    CallbackQueryHandler(
                        self.enter_media_name, pattern="^media_model_.*"
                    ),
                ],
                ENTER_MEDIA_NAME: [
                    CallbackQueryHandler(self.enter_media_name, pattern="^(media_model_.*|manage_cancel)$"),
                    MessageHandler(text_input_filter, self.enter_media_name),
                ],
                ENTER_MEDIA_QUANTITY: [
                    MessageHandler(text_input_filter, self.enter_media_quantity)
                ],
                CONFIRM_MEDIA_OPERATION: [
                    CallbackQueryHandler(
                        self.confirm_media_operation,
                        pattern="^(media_confirm|media_edit|manage_cancel)"
                    )
                ],
            },
            fallbacks=fallbacks,
        )
