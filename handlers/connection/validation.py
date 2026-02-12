"""
Проверка наличия материалов и роутеров у исполнителей
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

<<<<<<< Updated upstream
from config import SELECT_MATERIAL_PAYER, SELECT_ROUTER_PAYER
=======
from config import (
    SELECT_ROUTER_PAYER,
    SELECT_SNR_PAYER,
    SELECT_ONU_PAYER,
    SELECT_MEDIA_PAYER,
    SELECT_SFP_PAYER,
    SELECT_FIBER_PAYER,
    SELECT_TWISTED_EXTERNAL_PAYER,
    SELECT_TWISTED_INTERNAL_PAYER,
)
>>>>>>> Stashed changes
from utils.keyboards import get_main_keyboard
from database import Database


async def check_materials_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить балансы материалов и определить плательщика"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    fiber_meters = data['fiber_meters']
    twisted_pair_meters = data['twisted_pair_meters']
    
    # Получаем балансы всех выбранных сотрудников
    employees_with_balance = []
    for emp_id in selected_employees:
        emp = db.get_employee_by_id(emp_id)
        if emp:
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
            f"Управление сотрудниками → Управление материалами",
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
        context.user_data['material_payer_id'] = employees_with_enough[0]['id']
        # Переходим к проверке роутеров
        return await check_routers_and_proceed(update, context, db)
    
<<<<<<< Updated upstream
    else:
        # У нескольких есть материалы - предлагаем выбрать
        keyboard = []
        for emp in employees_with_enough:
            keyboard.append([InlineKeyboardButton(
                f"💰 {emp['name']} (ВОЛС: {emp['fiber']}м, ВП: {emp['twisted']}м)",
                callback_data=f"payer_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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


async def select_material_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора плательщика материалов"""
    query = update.callback_query
    await query.answer()
=======
    twisted_external_state = await _ensure_twisted_external_payer(update, context, db, selected_employees)
    if twisted_external_state is not None:
        return twisted_external_state

    twisted_internal_state = await _ensure_twisted_internal_payer(update, context, db, selected_employees)
    if twisted_internal_state is not None:
        return twisted_internal_state
>>>>>>> Stashed changes
    
    payer_id = int(query.data.split('_')[1])
    context.user_data['material_payer_id'] = payer_id
    
    db = Database()
    # Переходим к проверке роутеров
    return await check_routers_and_proceed(update, context, db)


<<<<<<< Updated upstream
=======
def _ensure_material_default(context, selected_employees):
    """Обновить общий материал-плательщика для обратной совместимости."""
    if context.user_data.get('material_payer_id'):
        return
    for key in ('fiber_payer_id', 'twisted_external_payer_id', 'twisted_internal_payer_id', 'twisted_payer_id'):
        payer_id = context.user_data.get(key)
        if payer_id:
            context.user_data['material_payer_id'] = payer_id
            if not context.user_data.get('twisted_payer_id'):
                context.user_data['twisted_payer_id'] = payer_id
            return
    if selected_employees:
        context.user_data['material_payer_id'] = selected_employees[0]


async def _ensure_fiber_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees
) -> int | None:
    """Проверить наличие ВОЛС у первого выбранного исполнителя."""
    data = context.user_data['connection_data']
    fiber_meters = float(data.get('fiber_meters') or 0)
    if fiber_meters <= 0:
        context.user_data['fiber_payer_id'] = None
        return None

    payer_id = selected_employees[0]
    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    payer_name = payer['full_name'] if payer else f"ID {payer_id}"
    available_meters = float((payer or {}).get('fiber_balance', 0) or 0)

    if available_meters < fiber_meters:
        query = update.callback_query
        error_text = (
            f"❌ <b>Недостаточно ВОЛС!</b>\n\n"
            f"Списание выполняется с первого выбранного исполнителя: <b>{payer_name}</b>\n"
            f"Требуется: {fiber_meters} м\n"
            f"Доступно у исполнителя: {available_meters} м\n\n"
            f"Добавьте ВОЛС на баланс указанного исполнителя."
        )
        if query:
            await query.edit_message_text(error_text, parse_mode='HTML')
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            await update.effective_message.reply_text(error_text, parse_mode='HTML')
            await update.effective_message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['fiber_payer_id'] = payer_id
    return None


async def _ensure_twisted_component_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees,
    *,
    data_key: str,
    balance_key: str,
    context_key: str,
    item_title: str,
    item_short: str,
    emoji: str,
    callback_prefix: str,
    target_state: int,
) -> int | None:
    """Убедиться, что выбран плательщик по компоненте витой пары."""
    data = context.user_data['connection_data']
    connection_type = data.get('connection_type')
    required_meters = float(data.get(data_key) or 0)

    if connection_type == 'magistral' or required_meters <= 0:
        context.user_data[context_key] = None
        return None

    query = update.callback_query
    employee_tasks = [run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees]
    employee_rows = await asyncio.gather(*employee_tasks, return_exceptions=False)

    candidates = []
    for emp_id, emp in zip(selected_employees, employee_rows):
        if not emp:
            continue
        balance = float(emp.get(balance_key, 0) or 0)
        candidates.append({
            'id': emp_id,
            'name': emp['full_name'],
            'balance': balance,
            'has_enough': balance >= required_meters
        })

    available = [emp for emp in candidates if emp['has_enough']]
    if not available:
        balances = '\n'.join(
            f"• {emp['name']}: {emp['balance']} м"
            for emp in candidates
        ) or "нет данных"
        await query.edit_message_text(
            f"❌ <b>Недостаточно {item_title.lower()}!</b>\n\n"
            f"Требуется: {required_meters} м\n"
            f"Балансы исполнителей:\n{balances}\n\n"
            f"Добавьте материалы через управление сотрудниками.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    if len(available) == 1:
        context.user_data[context_key] = available[0]['id']
        return None

    keyboard = [
        [InlineKeyboardButton(
            f"{emoji} {emp['name']} ({emp['balance']} м)",
            callback_data=f"{callback_prefix}_{emp['id']}"
        )]
        for emp in available
    ]
    reply_markup = build_inline_keyboard(keyboard)
    await query.edit_message_text(
        f"{emoji} <b>Выбор плательщика: {item_short}</b>\n\n"
        f"Требуется: {required_meters} м\n\n"
        f"Выберите сотрудника, с которого списать {item_title.lower()}:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    return target_state


async def _ensure_twisted_external_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees
) -> int | None:
    state = await _ensure_twisted_component_payer(
        update,
        context,
        db,
        selected_employees,
        data_key='twisted_pair_external_meters',
        balance_key='twisted_pair_external_balance',
        context_key='twisted_external_payer_id',
        item_title='внешней витой пары',
        item_short='Внеш. витая пара',
        emoji='🪢',
        callback_prefix='twisted_external_payer',
        target_state=SELECT_TWISTED_EXTERNAL_PAYER,
    )
    if state is None and context.user_data.get('twisted_external_payer_id') and not context.user_data.get('twisted_payer_id'):
        context.user_data['twisted_payer_id'] = context.user_data.get('twisted_external_payer_id')
    return state


async def _ensure_twisted_internal_payer(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    selected_employees
) -> int | None:
    return await _ensure_twisted_component_payer(
        update,
        context,
        db,
        selected_employees,
        data_key='twisted_pair_internal_meters',
        balance_key='twisted_pair_internal_balance',
        context_key='twisted_internal_payer_id',
        item_title='внутренней витой пары',
        item_short='Внут. витая пара',
        emoji='🪢',
        callback_prefix='twisted_internal_payer',
        target_state=SELECT_TWISTED_INTERNAL_PAYER,
    )


async def select_fiber_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика ВОЛС."""
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])
    context.user_data['fiber_payer_id'] = payer_id
    selected_employees = context.user_data.get('selected_employees', [])
    state = await _ensure_twisted_external_payer(update, context, db, selected_employees)
    if state is not None:
        return state
    state = await _ensure_twisted_internal_payer(update, context, db, selected_employees)
    if state is not None:
        return state
    _ensure_material_default(context, selected_employees)
    return await check_routers_and_proceed(update, context, db)


async def select_twisted_external_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика внешней витой пары."""
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[-1])
    context.user_data['twisted_external_payer_id'] = payer_id
    context.user_data['twisted_payer_id'] = payer_id
    selected_employees = context.user_data.get('selected_employees', [])
    state = await _ensure_twisted_internal_payer(update, context, db, selected_employees)
    if state is not None:
        return state
    _ensure_material_default(context, selected_employees)
    return await check_routers_and_proceed(update, context, db)


async def select_twisted_internal_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Обработка выбора плательщика внутренней витой пары."""
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[-1])
    context.user_data['twisted_internal_payer_id'] = payer_id
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
    """Проверить наличие ONU у первого выбранного исполнителя."""
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

    payer_id = selected_employees[0]
    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    payer_name = payer['full_name'] if payer else f"ID {payer_id}"
    available_qty = int(await run_in_thread(db.get_onu_quantity, payer_id, onu_model) or 0)

    if available_qty < onu_quantity:
        query = update.callback_query
        error_text = (
            f"❌ <b>Недостаточно ONU!</b>\n\n"
            f"Списание выполняется с первого выбранного исполнителя: <b>{payer_name}</b>\n"
            f"Требуется: <b>{onu_model}</b> — {onu_quantity} шт.\n"
            f"Доступно у исполнителя: {available_qty} шт.\n\n"
            f"Добавьте ONU на баланс указанного исполнителя."
        )
        if query:
            await query.edit_message_text(error_text, parse_mode='HTML')
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            await update.effective_message.reply_text(error_text, parse_mode='HTML')
            await update.effective_message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['onu_payer_id'] = payer_id
    return await check_media_and_proceed(update, context, db)


async def select_onu_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # onu_payer_<id>
    context.user_data['onu_payer_id'] = payer_id
    return await check_media_and_proceed(update, context, db)


async def check_media_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие медиаконверторов у первого выбранного исполнителя."""
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

    payer_id = selected_employees[0]
    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    payer_name = payer['full_name'] if payer else f"ID {payer_id}"
    available_qty = int(await run_in_thread(db.get_media_converter_quantity, payer_id, media_model) or 0)

    if available_qty < media_quantity:
        query = update.callback_query
        error_text = (
            f"❌ <b>Недостаточно медиаконверторов!</b>\n\n"
            f"Списание выполняется с первого выбранного исполнителя: <b>{payer_name}</b>\n"
            f"Требуется: <b>{media_model}</b> — {media_quantity} шт.\n"
            f"Доступно у исполнителя: {available_qty} шт.\n\n"
            f"Добавьте медиаконверторы на баланс указанного исполнителя."
        )
        if query:
            await query.edit_message_text(error_text, parse_mode='HTML')
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            await update.effective_message.reply_text(error_text, parse_mode='HTML')
            await update.effective_message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['media_payer_id'] = payer_id
    return await check_sfp_and_proceed(update, context, db)


async def select_media_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # media_payer_<id>
    context.user_data['media_payer_id'] = payer_id
    return await check_sfp_and_proceed(update, context, db)


async def check_sfp_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие SFP модулей у первого выбранного исполнителя."""
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

    payer_id = selected_employees[0]
    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    payer_name = payer['full_name'] if payer else f"ID {payer_id}"
    available_qty = int(await run_in_thread(db.get_sfp_module_quantity, payer_id, sfp_model) or 0)

    if available_qty < sfp_quantity:
        query = update.callback_query
        error_text = (
            f"❌ <b>Недостаточно SFP модулей!</b>\n\n"
            f"Списание выполняется с первого выбранного исполнителя: <b>{payer_name}</b>\n"
            f"Требуется: <b>{sfp_model}</b> — {sfp_quantity} шт.\n"
            f"Доступно у исполнителя: {available_qty} шт.\n\n"
            f"Добавьте SFP модули на баланс указанного исполнителя."
        )
        if query:
            await query.edit_message_text(error_text, parse_mode='HTML')
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            await update.effective_message.reply_text(error_text, parse_mode='HTML')
            await update.effective_message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['sfp_payer_id'] = payer_id
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)


async def select_sfp_payer(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    query = update.callback_query
    await query.answer()
    payer_id = int(query.data.split('_')[2])  # sfp_payer_<id>
    context.user_data['sfp_payer_id'] = payer_id
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)


>>>>>>> Stashed changes
async def check_routers_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие роутеров и определить плательщика"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    router_model = data['router_model']
    required_quantity = data.get('router_quantity', 1)
    
    # Если роутер пропущен, сразу переходим к подтверждению
    if router_model == '-' or not router_model:
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)
    
    # Получаем информацию о роутерах у сотрудников
    employees_with_router = []
    for emp_id in selected_employees:
        emp = db.get_employee_by_id(emp_id)
        if emp:
            router_quantity = db.get_router_quantity(emp_id, router_model)
            has_enough = router_quantity >= required_quantity
            employees_with_router.append({
                'id': emp_id,
                'name': emp['full_name'],
                'quantity': router_quantity,
                'has_enough': has_enough
            })
    
    # Определяем, у кого есть достаточно роутеров
    employees_with_enough = [e for e in employees_with_router if e['has_enough']]
    
    if len(employees_with_enough) == 0:
        # Ни у кого нет достаточно роутеров
        emp_list = '\n'.join([
            f"• {e['name']}: {e['quantity']} шт."
            for e in employees_with_router
        ])
        
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        await query.edit_message_text(
            f"❌ <b>Недостаточно роутеров!</b>\n\n"
            f"Требуется роутер: <b>{router_model}</b> - {quantity_text}\n\n"
            f"Балансы исполнителей:\n{emp_list}\n\n"
            f"Добавьте роутеры через:\n"
            f"Управление сотрудниками → Управление роутерами",
            parse_mode='HTML'
        )
<<<<<<< Updated upstream
        await query.message.reply_text(
            "Выберите действие:",
=======
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
    """Проверить наличие SNR боксов у первого выбранного исполнителя."""
    data = context.user_data['connection_data']
    snr_model = data.get('snr_box_model', '-')
    snr_quantity = data.get('snr_box_quantity', 0) or 0
    selected_employees = context.user_data.get('selected_employees', [])
    if not snr_model or snr_model == '-' or snr_quantity <= 0:
        return await check_onu_and_proceed(update, context, db)
    
    if not selected_employees:
        await update.effective_message.reply_text(
            "❌ Нет выбранных сотрудников для списания SNR бокса.",
>>>>>>> Stashed changes
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
<<<<<<< Updated upstream
    elif len(employees_with_enough) == 1:
        # Только у одного есть достаточно роутеров
        context.user_data['router_payer_id'] = employees_with_enough[0]['id']
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)
    
    else:
        # У нескольких есть достаточно роутеров - предлагаем выбрать
        keyboard = []
        for emp in employees_with_enough:
            keyboard.append([InlineKeyboardButton(
                f"📡 {emp['name']} ({emp['quantity']} шт.)",
                callback_data=f"router_payer_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        await query.edit_message_text(
            f"📡 <b>Выбор плательщика роутера</b>\n\n"
            f"Роутер: {router_model} - {quantity_text}\n\n"
            f"У нескольких исполнителей есть достаточно роутеров.\n"
            f"Выберите, с кого списать роутер:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return SELECT_ROUTER_PAYER


async def select_router_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора плательщика роутера"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[-1])
    context.user_data['router_payer_id'] = payer_id
    
    db = Database()
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)

=======
    payer_id = selected_employees[0]
    payer = await run_in_thread(db.get_employee_by_id, payer_id)
    payer_name = payer['full_name'] if payer else f"ID {payer_id}"
    available_qty = int(await run_in_thread(db.get_snr_box_quantity, payer_id, snr_model) or 0)

    if available_qty < snr_quantity:
        query = update.callback_query
        error_text = (
            f"❌ <b>Недостаточно SNR боксов!</b>\n\n"
            f"Списание выполняется с первого выбранного исполнителя: <b>{payer_name}</b>\n"
            f"Требуется: <b>{snr_model}</b> — {snr_quantity} шт.\n"
            f"Доступно у исполнителя: {available_qty} шт.\n\n"
            f"Добавьте боксы на баланс указанного исполнителя."
        )
        if query:
            await query.edit_message_text(error_text, parse_mode='HTML')
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            await update.effective_message.reply_text(error_text, parse_mode='HTML')
            await update.effective_message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    context.user_data['snr_box_payer_id'] = payer_id
    return await check_onu_and_proceed(update, context, db)
>>>>>>> Stashed changes
