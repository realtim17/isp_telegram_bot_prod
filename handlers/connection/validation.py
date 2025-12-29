"""
Проверка наличия материалов и роутеров у исполнителей
"""
import asyncio

from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_ROUTER_PAYER,
    SELECT_SNR_PAYER,
    SELECT_ONU_PAYER,
    SELECT_MEDIA_PAYER,
    SELECT_SFP_PAYER,
    SELECT_FIBER_PAYER,
    SELECT_TWISTED_PAYER,
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread
from handlers.connection.ui import build_inline_keyboard


async def check_materials_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить балансы материалов и определить плательщиков для ВОЛС/ВП."""
    selected_employees = context.user_data.get('selected_employees', [])
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных исполнителей для списания материалов.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    fiber_state = await _ensure_fiber_payer(update, context, db, selected_employees)
    if fiber_state is not None:
        return fiber_state
    
    twisted_state = await _ensure_twisted_payer(update, context, db, selected_employees)
    if twisted_state is not None:
        return twisted_state
    
    _ensure_material_default(context, selected_employees)
    
    return await check_routers_and_proceed(update, context, db)


def _ensure_material_default(context, selected_employees):
    """Обновить общий материал-плательщика для обратной совместимости."""
    if context.user_data.get('material_payer_id'):
        return
    for key in ('fiber_payer_id', 'twisted_payer_id'):
        payer_id = context.user_data.get(key)
        if payer_id:
            context.user_data['material_payer_id'] = payer_id
            return
    if selected_employees:
        context.user_data['material_payer_id'] = selected_employees[0]


async def _ensure_fiber_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees
) -> int | None:
    """Убедиться, что выбран плательщик по ВОЛС."""
    data = context.user_data['connection_data']
    fiber_meters = float(data.get('fiber_meters') or 0)
    if fiber_meters <= 0:
        context.user_data['fiber_payer_id'] = None
        return None
    
    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    employee_rows = await asyncio.gather(*employee_tasks, return_exceptions=False)
    
    candidates = []
    for emp_id, emp in zip(selected_employees, employee_rows):
        if not emp:
            continue
        fiber_balance = float(emp.get('fiber_balance', 0) or 0)
        candidates.append({
            'id': emp_id,
            'name': emp['full_name'],
            'balance': fiber_balance,
            'has_enough': fiber_balance >= fiber_meters
        })
    
    available = [emp for emp in candidates if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['balance']} м"
            for emp in candidates
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно ВОЛС!</b>\n\n"
            f"Требуется: {fiber_meters} м\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте материалы через управление сотрудниками.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END
    
    if len(available) == 1:
        context.user_data['fiber_payer_id'] = available[0]['id']
        return None
    
    keyboard = [
        [InlineKeyboardButton(
            f"🧵 {emp['name']} ({emp['balance']} м)",
            callback_data=f"fiber_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🧵 <b>Выбор плательщика ВОЛС</b>\n\n"
        f"Требуется: {fiber_meters} м\n\n"
        f"Выберите сотрудника, с которого списать ВОЛС:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_FIBER_PAYER


async def _ensure_twisted_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees
) -> int | None:
    """Убедиться, что выбран плательщик по витой паре (если требуется)."""
    data = context.user_data['connection_data']
    connection_type = data.get('connection_type')
    twisted_pair_meters = float(data.get('twisted_pair_meters') or 0)
    if connection_type == 'magistral' or twisted_pair_meters <= 0:
        context.user_data['twisted_payer_id'] = None
        return None
    
    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    employee_rows = await asyncio.gather(*employee_tasks, return_exceptions=False)
    
    candidates = []
    for emp_id, emp in zip(selected_employees, employee_rows):
        if not emp:
            continue
        twisted_balance = float(emp.get('twisted_pair_balance', 0) or 0)
        candidates.append({
            'id': emp_id,
            'name': emp['full_name'],
            'balance': twisted_balance,
            'has_enough': twisted_balance >= twisted_pair_meters
        })
    
    available = [emp for emp in candidates if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['balance']} м"
            for emp in candidates
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно витой пары!</b>\n\n"
            f"Требуется: {twisted_pair_meters} м\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте материалы через управление сотрудниками.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END
    
    if len(available) == 1:
        context.user_data['twisted_payer_id'] = available[0]['id']
        return None
    
    keyboard = [
        [InlineKeyboardButton(
            f"🪢 {emp['name']} ({emp['balance']} м)",
            callback_data=f"twisted_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🪢 <b>Выбор плательщика витой пары</b>\n\n"
        f"Требуется: {twisted_pair_meters} м\n\n"
        f"Выберите сотрудника, с которого списать витую пару:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_TWISTED_PAYER


async def select_fiber_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика ВОЛС."""
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])
    context.user_data['fiber_payer_id'] = payer_id
    selected_employees = context.user_data.get('selected_employees', [])
    state = await _ensure_twisted_payer(update, context, db, selected_employees)
    if state is not None:
        return state
    _ensure_material_default(context, selected_employees)
    return await check_routers_and_proceed(update, context, db)


async def select_twisted_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика витой пары."""
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])
    context.user_data['twisted_payer_id'] = payer_id
    selected_employees = context.user_data.get('selected_employees', [])
    _ensure_material_default(context, selected_employees)
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
    
    # Переходим к проверке ONU/прочего оборудования
    return await check_onu_and_proceed(update, context, db)


async def check_onu_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие ONU у выбранных сотрудников и предложить выбрать плательщика."""
    data = context.user_data['connection_data']
    onu_model = data.get('onu_model', '-') or '-'
    onu_quantity = int(data.get('onu_quantity', 0) or 0)

    if onu_model == '-' or onu_quantity <= 0:
        return await check_media_and_proceed(update, context, db)

    selected_employees = context.user_data.get('selected_employees', [])
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания ONU.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    quantity_tasks = [run_in_thread(db.get_onu_quantity, emp_id, onu_model) for emp_id in selected_employees]
    employees = await asyncio.gather(*employee_tasks, return_exceptions=False)
    quantities = await asyncio.gather(*quantity_tasks, return_exceptions=False)

    employees_with_onu = []
    for emp_id, emp, qty in zip(selected_employees, employees, quantities):
        if not emp:
            continue
        quantity = int(qty or 0)
        employees_with_onu.append({
            'id': emp_id,
            'name': emp['full_name'],
            'quantity': quantity,
            'has_enough': quantity >= onu_quantity
        })

    available = [emp for emp in employees_with_onu if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['quantity']} шт."
            for emp in employees_with_onu
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно ONU!</b>\n\n"
            f"Требуется: <b>{onu_model}</b> — {onu_quantity} шт.\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте ONU на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data['onu_payer_id'] = available[0]['id']
        return await check_media_and_proceed(update, context, db)

    keyboard = [
        [InlineKeyboardButton(
            f"🔌 {emp['name']} ({emp['quantity']} шт.)",
            callback_data=f"onu_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🔌 <b>Выбор плательщика ONU</b>\n\n"
        f"Требуется: <b>{onu_model}</b> — {onu_quantity} шт.\n\n"
        f"Выберите сотрудника, с которого списать ONU:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_ONU_PAYER


async def select_onu_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # onu_payer_<id>
    context.user_data['onu_payer_id'] = payer_id
    return await check_media_and_proceed(update, context, db)


async def check_media_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие медиаконверторов и предложить выбрать плательщика."""
    data = context.user_data['connection_data']
    media_model = data.get('media_converter_model', '-') or '-'
    media_quantity = int(data.get('media_converter_quantity', 0) or 0)

    if media_model == '-' or media_quantity <= 0:
        return await check_sfp_and_proceed(update, context, db)

    selected_employees = context.user_data.get('selected_employees', [])
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания медиаконверторов.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    quantity_tasks = [
        run_in_thread(db.get_media_converter_quantity, emp_id, media_model)
        for emp_id in selected_employees
    ]
    employees = await asyncio.gather(*employee_tasks, return_exceptions=False)
    quantities = await asyncio.gather(*quantity_tasks, return_exceptions=False)

    employees_with_media = []
    for emp_id, emp, qty in zip(selected_employees, employees, quantities):
        if not emp:
            continue
        quantity = int(qty or 0)
        employees_with_media.append({
            'id': emp_id,
            'name': emp['full_name'],
            'quantity': quantity,
            'has_enough': quantity >= media_quantity
        })

    available = [emp for emp in employees_with_media if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['quantity']} шт."
            for emp in employees_with_media
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно медиаконверторов!</b>\n\n"
            f"Требуется: <b>{media_model}</b> — {media_quantity} шт.\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте медиаконверторы на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data['media_payer_id'] = available[0]['id']
        return await check_sfp_and_proceed(update, context, db)

    keyboard = [
        [InlineKeyboardButton(
            f"🔄 {emp['name']} ({emp['quantity']} шт.)",
            callback_data=f"media_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🔄 <b>Выбор плательщика медиаконверторов</b>\n\n"
        f"Требуется: <b>{media_model}</b> — {media_quantity} шт.\n\n"
        f"Выберите сотрудника, с которого списать оборудование:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_MEDIA_PAYER


async def select_media_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # media_payer_<id>
    context.user_data['media_payer_id'] = payer_id
    return await check_sfp_and_proceed(update, context, db)


async def check_sfp_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие SFP модулей и предложить выбрать плательщика."""
    data = context.user_data['connection_data']
    sfp_model = data.get('sfp_module_model', '-') or '-'
    sfp_quantity = int(data.get('sfp_module_quantity', 0) or 0)

    if sfp_model == '-' or sfp_quantity <= 0:
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)

    selected_employees = context.user_data.get('selected_employees', [])
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания SFP модулей.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    quantity_tasks = [run_in_thread(db.get_sfp_module_quantity, emp_id, sfp_model) for emp_id in selected_employees]
    employees = await asyncio.gather(*employee_tasks, return_exceptions=False)
    quantities = await asyncio.gather(*quantity_tasks, return_exceptions=False)

    employees_with_sfp = []
    for emp_id, emp, qty in zip(selected_employees, employees, quantities):
        if not emp:
            continue
        quantity = int(qty or 0)
        employees_with_sfp.append({
            'id': emp_id,
            'name': emp['full_name'],
            'quantity': quantity,
            'has_enough': quantity >= sfp_quantity
        })

    available = [emp for emp in employees_with_sfp if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['quantity']} шт."
            for emp in employees_with_sfp
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно SFP модулей!</b>\n\n"
            f"Требуется: <b>{sfp_model}</b> — {sfp_quantity} шт.\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте SFP модули на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data['sfp_payer_id'] = available[0]['id']
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)

    keyboard = [
        [InlineKeyboardButton(
            f"🧿 {emp['name']} ({emp['quantity']} шт.)",
            callback_data=f"sfp_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🧿 <b>Выбор плательщика SFP модулей</b>\n\n"
        f"Требуется: <b>{sfp_model}</b> — {sfp_quantity} шт.\n\n"
        f"Выберите сотрудника, с которого списать модули:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_SFP_PAYER


async def select_sfp_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # sfp_payer_<id>
    context.user_data['sfp_payer_id'] = payer_id
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)


async def check_routers_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие роутеров у материально ответственного"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    router_model = data['router_model']
    required_quantity = data.get('router_quantity', 1)
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания роутера.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Если роутер пропущен, сразу переходим к подтверждению
    if router_model == '-' or not router_model:
        return await check_snr_boxes_and_proceed(update, context, db)
    
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    quantity_tasks = [run_in_thread(db.get_router_quantity, emp_id, router_model) for emp_id in selected_employees]
    employees = await asyncio.gather(*employee_tasks, return_exceptions=False)
    quantities = await asyncio.gather(*quantity_tasks, return_exceptions=False)

    employees_with_router = []
    for emp_id, emp, qty in zip(selected_employees, employees, quantities):
        if not emp:
            continue
        quantity = int(qty or 0)
        employees_with_router.append({
            'id': emp_id,
            'name': emp['full_name'],
            'quantity': quantity,
            'has_enough': quantity >= required_quantity
        })

    available = [emp for emp in employees_with_router if emp['has_enough']]
    if not available:
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        balances = '\n'.join(
            f"• {emp['name']}: {emp['quantity']} шт."
            for emp in employees_with_router
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно роутеров!</b>\n\n"
            f"Требуется: <b>{router_model}</b> — {quantity_text}\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте роутеры на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data['router_payer_id'] = available[0]['id']
        return await check_snr_boxes_and_proceed(update, context, db)

    keyboard = [
        [InlineKeyboardButton(
            f"📡 {emp['name']} ({emp['quantity']} шт.)",
            callback_data=f"router_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"📡 <b>Выбор плательщика роутеров</b>\n\n"
        f"Требуется: <b>{router_model}</b> — {required_quantity} шт.\n\n"
        f"Выберите, у кого списать роутеры:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_ROUTER_PAYER


async def check_snr_boxes_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие SNR боксов"""
    data = context.user_data['connection_data']
    snr_model = data.get('snr_box_model', '-')
    snr_quantity = data.get('snr_box_quantity', 0) or 0
    selected_employees = context.user_data.get('selected_employees', [])
    if not snr_model or snr_model == '-' or snr_quantity <= 0:
        return await check_onu_and_proceed(update, context, db)
    
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания SNR бокса.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    quantity_tasks = [run_in_thread(db.get_snr_box_quantity, emp_id, snr_model) for emp_id in selected_employees]
    employees = await asyncio.gather(*employee_tasks, return_exceptions=False)
    quantities = await asyncio.gather(*quantity_tasks, return_exceptions=False)

    employees_with_snr = []
    for emp_id, emp, qty in zip(selected_employees, employees, quantities):
        if not emp:
            continue
        quantity = int(qty or 0)
        employees_with_snr.append({
            'id': emp_id,
            'name': emp['full_name'],
            'quantity': quantity,
            'has_enough': quantity >= snr_quantity
        })

    available = [emp for emp in employees_with_snr if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['quantity']} шт."
            for emp in employees_with_snr
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно SNR боксов!</b>\n\n"
            f"Требуется бокс: <b>{snr_model}</b> — {snr_quantity} шт.\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте боксы на баланс материально ответственного.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data['snr_box_payer_id'] = available[0]['id']
        return await check_onu_and_proceed(update, context, db)

    keyboard = [
        [InlineKeyboardButton(
            f"🧰 {emp['name']} ({emp['quantity']} шт.)",
            callback_data=f"snr_payer_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"🧰 <b>Выбор плательщика SNR боксов</b>\n\n"
        f"Требуется: <b>{snr_model}</b> — {snr_quantity} шт.\n\n"
        f"Выберите, у кого списать боксы:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return SELECT_SNR_PAYER
