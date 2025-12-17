"""
Проверка наличия материалов и роутеров у исполнителей
"""
import asyncio

from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from config import SELECT_MATERIAL_PAYER, SELECT_ROUTER_PAYER, SELECT_SNR_PAYER
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread
from handlers.connection.ui import build_inline_keyboard


def _set_responsible(context, payer_id: int) -> None:
    """Зафиксировать единственного материально-ответственного для всех списаний."""
    context.user_data['material_payer_id'] = payer_id
    context.user_data['router_payer_id'] = payer_id
    context.user_data['snr_box_payer_id'] = payer_id
    context.user_data['onu_payer_id'] = payer_id
    context.user_data['media_payer_id'] = payer_id
    context.user_data['sfp_payer_id'] = payer_id


async def check_materials_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить балансы материалов и определить плательщика"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    fiber_meters = data['fiber_meters']
    twisted_pair_meters = data['twisted_pair_meters']
    
    # Получаем балансы всех выбранных сотрудников (параллельно)
    employees_with_balance = []
    if selected_employees:
        employee_tasks = [
            run_in_thread(db.get_employee_by_id, emp_id)
            for emp_id in selected_employees
        ]
        employee_rows = await asyncio.gather(*employee_tasks, return_exceptions=False)
        for emp_id, emp in zip(selected_employees, employee_rows):
            if not emp:
                continue
            fiber_balance = emp.get('fiber_balance', 0) or 0
            twisted_balance = emp.get('twisted_pair_balance', 0) or 0
            has_enough = (fiber_balance >= fiber_meters and twisted_balance >= twisted_pair_meters)
            employees_with_balance.append({
                'id': emp_id,
                'name': emp['full_name'],
                'fiber': fiber_balance,
                'twisted': twisted_balance,
                'has_enough': has_enough
            })
    
    # Определяем, у кого есть достаточно материалов
    employees_with_enough = [e for e in employees_with_balance if e['has_enough']]
    
    if len(employees_with_enough) == 0:
        # Ни у кого нет достаточно материалов
        emp_list = '\n'.join([
            f"• {e['name']}: ВОЛС {e['fiber']}м, ВП {e['twisted']}м"
            for e in employees_with_balance
        ])
        
        await query.edit_message_text(
            f"❌ <b>Недостаточно материалов!</b>\n\n"
            f"Требуется:\n"
            f"• ВОЛС: {fiber_meters} м\n"
            f"• Витая пара: {twisted_pair_meters} м\n\n"
            f"Балансы исполнителей:\n{emp_list}\n\n"
            f"Добавьте материалы через:\n"
            f"Управление сотрудниками → 🧵 ВОЛС / ВИТ.ПАРА",
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    elif len(employees_with_enough) == 1:
        # Только у одного есть материалы - списываем с него автоматически
        _set_responsible(context, employees_with_enough[0]['id'])
        # Переходим к проверке роутеров для этого же ответственного
        return await check_routers_and_proceed(update, context, db)
    
    else:
        # У нескольких есть материалы - предлагаем выбрать
        keyboard = [
            [InlineKeyboardButton(
                f"💰 {emp['name']} (ВОЛС: {emp['fiber']}м, ВП: {emp['twisted']}м)",
                callback_data=f"payer_{emp['id']}"
            )]
            for emp in employees_with_enough
        ]
        reply_markup = build_inline_keyboard(keyboard)
        
        await query.edit_message_text(
            f"💰 <b>Выбор плательщика материалов</b>\n\n"
            f"Требуется:\n"
            f"• ВОЛС: {fiber_meters} м\n"
            f"• Витая пара: {twisted_pair_meters} м\n\n"
            f"У нескольких исполнителей есть достаточно материалов.\n"
            f"Выберите, с кого списать материалы:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return SELECT_MATERIAL_PAYER


async def select_material_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика материалов"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[1])
    _set_responsible(context, payer_id)
    
    # Переходим к проверке роутеров для того же ответственного
    return await check_routers_and_proceed(update, context, db)


async def select_router_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика роутера"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[2])  # router_payer_<id>
    context.user_data['router_payer_id'] = payer_id
    
    # Переходим к проверке SNR боксов
    return await check_snr_boxes_and_proceed(update, context, db)


async def select_snr_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика SNR бокса"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[2])  # snr_payer_<id>
    context.user_data['snr_box_payer_id'] = payer_id
    
    # Переходим к подтверждению
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)


async def check_routers_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие роутеров у материально ответственного"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    router_model = data['router_model']
    required_quantity = data.get('router_quantity', 1)
    payer_id = context.user_data.get('material_payer_id') or (selected_employees[0] if selected_employees else None)
    if payer_id:
        context.user_data['router_payer_id'] = payer_id
    
    # Если роутер пропущен, сразу переходим к подтверждению
    if router_model == '-' or not router_model:
        return await check_snr_boxes_and_proceed(update, context, db)
    
    if not payer_id:
        await query.edit_message_text(
            "❌ Не выбран материально ответственный для списания роутера.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END

    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    quantity = await run_in_thread(db.get_router_quantity, payer_id, router_model)
    if quantity < required_quantity:
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        await query.edit_message_text(
            f"❌ <b>Недостаточно роутеров!</b>\n\n"
            f"Требуется: <b>{router_model}</b> - {quantity_text}\n"
            f"У {payer['full_name']} доступно: {quantity} шт.\n\n"
            f"Добавьте роутеры на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    # Переходим к проверке SNR для того же ответственного
    return await check_snr_boxes_and_proceed(update, context, db)


async def check_snr_boxes_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие SNR боксов"""
    data = context.user_data['connection_data']
    snr_model = data.get('snr_box_model', '-')
    snr_quantity = data.get('snr_box_quantity', 0) or 0
    payer_id = context.user_data.get('material_payer_id')
    if payer_id:
        context.user_data['snr_box_payer_id'] = payer_id
    
    if not snr_model or snr_model == '-' or snr_quantity <= 0:
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)
    
    selected_employees = context.user_data.get('selected_employees', [])
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания SNR бокса.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    query = update.callback_query
    if not payer_id:
        await query.edit_message_text(
            "❌ Не выбран материально ответственный для списания SNR бокса.",
            parse_mode='HTML'
        )
        context.user_data.clear()
        return ConversationHandler.END

    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    quantity = await run_in_thread(db.get_snr_box_quantity, payer_id, snr_model)
    if quantity < snr_quantity:
        await query.edit_message_text(
            f"❌ <b>Недостаточно SNR боксов!</b>\n\n"
            f"Требуется бокс: <b>{snr_model}</b>\n"
            f"Требуемое количество: {snr_quantity} шт.\n"
            f"У {payer['full_name']} доступно: {quantity} шт.\n\n"
            f"Добавьте боксы на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)
