"""
Подтверждение данных и сохранение подключения
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import CONFIRM, CONNECTION_TYPES, logger
from utils.keyboards import get_main_keyboard
from utils.helpers import send_connection_report
from database import Database


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Показать подтверждение перед сохранением"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    data.setdefault('bitrix_task_url', '-')
    data.setdefault('account_number', '-')
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    
    # Получаем имена выбранных сотрудников
    employees = db.get_all_employees()
    employee_names = [emp['full_name'] for emp in employees if emp['id'] in selected_employees]
    
    # Получаем читаемое название типа подключения
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
<<<<<<< Updated upstream
    # Рассчитываем долю на каждого
    emp_count = len(selected_employees)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    # Получаем информацию о плательщиках
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    
    payer_info = ""
    if material_payer_id:
        payer = db.get_employee_by_id(material_payer_id)
        if payer:
            payer_info += f"\n\n💰 <b>Материалы списываются с:</b> {payer['full_name']}"
    
    if router_payer_id:
        router_payer = db.get_employee_by_id(router_payer_id)
        if router_payer:
            router_quantity = data.get('router_quantity', 1)
            quantity_text = f" ({router_quantity} шт.)" if router_quantity > 1 else ""
            payer_info += f"\n📡 <b>Роутер списывается с:</b> {router_payer['full_name']}{quantity_text}"
=======
    # Нормализуем метраж внешней/внутренней витой пары и общий итог
    twisted_external = float(data.get('twisted_pair_external_meters') or 0)
    twisted_internal = float(data.get('twisted_pair_internal_meters') or 0)
    twisted_total = float(data.get('twisted_pair_meters') or 0)
    if twisted_external == 0 and twisted_internal == 0 and twisted_total > 0:
        twisted_external = round(twisted_total / 2, 2)
        twisted_internal = round(twisted_total - twisted_external, 2)
    elif twisted_total == 0 and (twisted_external or twisted_internal):
        twisted_total = twisted_external + twisted_internal
    data['twisted_pair_external_meters'] = twisted_external
    data['twisted_pair_internal_meters'] = twisted_internal
    data['twisted_pair_meters'] = twisted_total

    # Единый материально ответственный для всех списаний
    material_payer_id = context.user_data.get('material_payer_id')
    if not material_payer_id and selected_employees:
        material_payer_id = selected_employees[0]
        context.user_data['material_payer_id'] = material_payer_id
    first_employee_id = selected_employees[0] if selected_employees else None
    # По бизнес-правилу ВОЛС списывается с первого выбранного исполнителя.
    fiber_payer_id = first_employee_id or context.user_data.get('fiber_payer_id') or material_payer_id
    twisted_external_payer_id = (
        context.user_data.get('twisted_external_payer_id')
        or context.user_data.get('twisted_payer_id')
        or material_payer_id
    )
    twisted_internal_payer_id = (
        context.user_data.get('twisted_internal_payer_id')
        or context.user_data.get('twisted_payer_id')
        or twisted_external_payer_id
        or material_payer_id
    )
    router_payer_id = context.user_data.get('router_payer_id') or material_payer_id
    # По бизнес-правилу эти ТМЦ всегда списываются с первого выбранного исполнителя.
    snr_box_payer_id = first_employee_id or material_payer_id
    onu_payer_id = first_employee_id or material_payer_id
    media_payer_id = first_employee_id or material_payer_id
    sfp_payer_id = first_employee_id or material_payer_id
    context.user_data['router_payer_id'] = router_payer_id
    context.user_data['snr_box_payer_id'] = snr_box_payer_id
    context.user_data['onu_payer_id'] = onu_payer_id
    context.user_data['media_payer_id'] = media_payer_id
    context.user_data['sfp_payer_id'] = sfp_payer_id
    context.user_data['fiber_payer_id'] = fiber_payer_id
    context.user_data['twisted_external_payer_id'] = twisted_external_payer_id
    context.user_data['twisted_internal_payer_id'] = twisted_internal_payer_id
    context.user_data['twisted_payer_id'] = twisted_external_payer_id
    
    async def _ensure_employee(emp_id: int | None):
        if not emp_id:
            return None
        employee = employee_map.get(emp_id)
        if not employee:
            employee = await run_in_thread(db.get_employee_by_id, emp_id)
            if employee:
                employee_map[emp_id] = employee
        return employee

    payer_names = {}

    async def _assign_payer_name(key: str, emp_id: int | None):
        if not emp_id:
            return
        employee = await _ensure_employee(emp_id)
        if employee:
            payer_names[key] = employee['full_name']

    await _assign_payer_name('fiber', fiber_payer_id)
    await _assign_payer_name('twisted_external', twisted_external_payer_id)
    await _assign_payer_name('twisted_internal', twisted_internal_payer_id)
    await _assign_payer_name('twisted', twisted_external_payer_id)
    await _assign_payer_name('router', router_payer_id)
    await _assign_payer_name('snr', snr_box_payer_id)
    await _assign_payer_name('onu', onu_payer_id)
    await _assign_payer_name('media', media_payer_id)
    await _assign_payer_name('sfp', sfp_payer_id)
>>>>>>> Stashed changes
    
    # Формируем отображение роутера
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    
    if router_model == '-' or not router_model:
        router_display = "-"
    else:
        router_display = router_model
        if router_quantity > 1:
            router_display += f" ({router_quantity} шт.)"
    
    # Формируем отображение порта
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подписан" if contract_signed else "❌ Не подписан"
    
    # Получаем информацию о доступе на роутер
    router_access = data.get('router_access', False)
    router_access_status = "✅ Получен" if router_access else "⏭️ Пропущено"
    
    # Получаем информацию о Телеграмм Боте
    telegram_bot_connected = data.get('telegram_bot_connected', False)
    telegram_bot_status = "✅ Подключен" if telegram_bot_connected else "-"
    
    confirmation_text = f"""
<b>📋 Подтверждение данных</b>

<b>📍 Адрес:</b> {data['address']}

<b>Тип подключения:</b> {type_name}
<b>Модель роутера:</b> {router_display}
<b>Доступ на роутер:</b> {router_access_status}
<b>Договор:</b> {contract_status}
<b>Телеграмм Бот:</b> {telegram_bot_status}
<b>Порт:</b> {port_display}

<b>📏 Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

<b>👥 Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

<b>💡 Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м{payer_info}

<b>📸 Фото:</b> {len(photos)} шт.

Всё верно? Подтвердите создание отчета.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_yes')],
        [InlineKeyboardButton("❌ Отменить", callback_data='confirm_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return CONFIRM


async def confirm_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и сохранение подключения"""
    query = update.callback_query
    await query.answer()
<<<<<<< Updated upstream
    
    if query.data == 'confirm_no':
=======
    try:
        if query.data == 'confirm_no':
            context.user_data.clear()
            await query.edit_message_text(
                "❌ Создание отчета отменено.",
                reply_markup=None
            )
            await query.message.reply_text(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        # Сохраняем в БД
        data = context.user_data.get('connection_data')
        selected_employees = context.user_data.get('selected_employees', [])
        if not data or not selected_employees:
            context.user_data.clear()
            await query.edit_message_text(
                "❌ Недостаточно данных для сохранения отчета. Попробуйте начать заново.",
                reply_markup=None,
                parse_mode='HTML'
            )
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        photos = context.user_data.get('photos', [])
        material_payer_id = context.user_data.get('material_payer_id')
        first_employee_id = selected_employees[0] if selected_employees else None
        # По бизнес-правилу ВОЛС списывается с первого выбранного исполнителя.
        fiber_payer_id = first_employee_id or context.user_data.get('fiber_payer_id')
        twisted_external_payer_id = (
            context.user_data.get('twisted_external_payer_id')
            or context.user_data.get('twisted_payer_id')
        )
        twisted_internal_payer_id = (
            context.user_data.get('twisted_internal_payer_id')
            or context.user_data.get('twisted_payer_id')
            or twisted_external_payer_id
        )
        router_payer_id = context.user_data.get('router_payer_id')
        # По бизнес-правилу эти ТМЦ всегда списываются с первого выбранного исполнителя.
        snr_box_payer_id = first_employee_id or context.user_data.get('snr_box_payer_id')
        onu_payer_id = first_employee_id or context.user_data.get('onu_payer_id')
        media_payer_id = first_employee_id or context.user_data.get('media_payer_id')
        sfp_payer_id = first_employee_id or context.user_data.get('sfp_payer_id')
        twisted_pair_external_meters = float(data.get('twisted_pair_external_meters') or 0)
        twisted_pair_internal_meters = float(data.get('twisted_pair_internal_meters') or 0)
        twisted_pair_meters = float(data.get('twisted_pair_meters') or 0)
        if twisted_pair_external_meters == 0 and twisted_pair_internal_meters == 0 and twisted_pair_meters > 0:
            twisted_pair_external_meters = round(twisted_pair_meters / 2, 2)
            twisted_pair_internal_meters = round(twisted_pair_meters - twisted_pair_external_meters, 2)
        elif twisted_pair_meters == 0 and (twisted_pair_external_meters or twisted_pair_internal_meters):
            twisted_pair_meters = twisted_pair_external_meters + twisted_pair_internal_meters
        data['twisted_pair_external_meters'] = twisted_pair_external_meters
        data['twisted_pair_internal_meters'] = twisted_pair_internal_meters
        data['twisted_pair_meters'] = twisted_pair_meters
        payer_ids = {
            'fiber': fiber_payer_id,
            'twisted': twisted_external_payer_id,
            'twisted_external': twisted_external_payer_id,
            'twisted_internal': twisted_internal_payer_id,
            'router': router_payer_id,
            'snr': snr_box_payer_id,
            'onu': onu_payer_id,
            'media': media_payer_id,
            'sfp': sfp_payer_id,
        }
        user_id = update.effective_user.id
        
        onu_model = data.get('onu_model', '-')
        onu_quantity = data.get('onu_quantity', 0) or 0
        media_model = data.get('media_converter_model', '-')
        media_quantity = data.get('media_converter_quantity', 0) or 0
        sfp_model = data.get('sfp_module_model', '-')
        sfp_quantity = data.get('sfp_module_quantity', 0) or 0
        
        router_quantity = data.get('router_quantity', 1)
        contract_signed = data.get('contract_signed', False)
        router_access = data.get('router_access', False)
        telegram_bot_connected = data.get('telegram_bot_connected', False)
        snr_box_model = data.get('snr_box_model', '-')
        snr_box_quantity = data.get('snr_box_quantity', 0) or 0
        
        try:
            connection_id = await run_in_thread(
                db.create_connection,
                connection_type=data.get('connection_type', 'mkd'),
                address=data['address'],
                router_model=data['router_model'],
                snr_box_model=snr_box_model,
                port=data['port'],
                fiber_meters=data['fiber_meters'],
                twisted_pair_meters=twisted_pair_meters,
                twisted_pair_external_meters=twisted_pair_external_meters,
                twisted_pair_internal_meters=twisted_pair_internal_meters,
                fiber_payer_id=fiber_payer_id,
                twisted_payer_id=twisted_external_payer_id,
                twisted_external_payer_id=twisted_external_payer_id,
                twisted_internal_payer_id=twisted_internal_payer_id,
                hooks_quantity=data.get('hooks_quantity', 0),
                ork_quantity=data.get('ork_quantity', 0),
                mufta_quantity=data.get('mufta_quantity', 0),
                employee_ids=selected_employees,
                photo_file_ids=photos,
                created_by=user_id,
                material_payer_id=material_payer_id,
                router_quantity=router_quantity,
                contract_signed=contract_signed,
                router_access=router_access,
                telegram_bot_connected=telegram_bot_connected,
                router_payer_id=router_payer_id,
                snr_box_payer_id=snr_box_payer_id,
                snr_box_quantity=snr_box_quantity,
                onu_model=onu_model,
                onu_quantity=onu_quantity,
                onu_payer_id=onu_payer_id,
                media_converter_model=media_model,
                media_converter_quantity=media_quantity,
                media_payer_id=media_payer_id,
                sfp_module_model=sfp_model,
                sfp_module_quantity=sfp_quantity,
                sfp_payer_id=sfp_payer_id,
                bitrix_task_url=data.get('bitrix_task_url', '-'),
                account_number=str(data.get('account_number', '-') or '-'),
                comment=data.get('comment', ''),
            )
        except Exception as exc:
            logger.exception("Ошибка при сохранении подключения: %s", exc)
            context.user_data.clear()
            reason = str(exc) or "Неизвестная ошибка"
            await query.edit_message_text(
                f"❌ Не удалось сохранить подключение: {reason}",
                parse_mode='HTML'
            )
            await query.message.reply_text(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        if connection_id:
            await query.edit_message_text(
                f"✅ <b>Отчет успешно создан!</b>\n\n"
                f"ID подключения: #{connection_id}\n"
                f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                parse_mode='HTML'
            )
            
            await send_connection_report(
                query.message,
                connection_id,
                data,
                photos,
                selected_employees,
                db,
                payer_ids=payer_ids,
            )
            
            await query.message.reply_text(
                "Выберите следующее действие:",
                reply_markup=get_main_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при создании отчета. Попробуйте позже.",
                parse_mode='HTML'
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as exc:
        logger.exception("Ошибка при подтверждении подключения: %s", exc)
>>>>>>> Stashed changes
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Создание отчета отменено.",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем в БД
    db = Database()
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    user_id = update.effective_user.id
    
    router_quantity = data.get('router_quantity', 1)
    contract_signed = data.get('contract_signed', False)
    router_access = data.get('router_access', False)
    telegram_bot_connected = data.get('telegram_bot_connected', False)
    
    connection_id = db.create_connection(
        connection_type=data.get('connection_type', 'mkd'),
        address=data['address'],
        router_model=data['router_model'],
        port=data['port'],
        fiber_meters=data['fiber_meters'],
        twisted_pair_meters=data['twisted_pair_meters'],
        employee_ids=selected_employees,
        photo_file_ids=photos,
        created_by=user_id,
        material_payer_id=material_payer_id,
        router_quantity=router_quantity,
        contract_signed=contract_signed,
        router_access=router_access,
        telegram_bot_connected=telegram_bot_connected
    )
    
    if connection_id:
        # Списываем роутер, если указан плательщик и роутер не пропущен
        router_model = data.get('router_model', '-')
        if router_payer_id and router_model != '-' and router_model:
            success = db.deduct_router_from_employee(
                router_payer_id, 
                router_model, 
                router_quantity,
                connection_id=connection_id,
                created_by=user_id
            )
            if success:
                logger.info(f"Роутер '{router_model}' x{router_quantity} списан с сотрудника ID {router_payer_id}")
            else:
                logger.warning(f"Не удалось списать роутер '{router_model}' x{router_quantity} с сотрудника ID {router_payer_id}")
        
        # Отправляем подтверждение
        await query.edit_message_text(
            f"✅ <b>Отчет успешно создан!</b>\n\n"
            f"ID подключения: #{connection_id}\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Отправляем отчет с фотографиями
        await send_connection_report(query.message, connection_id, data, photos, selected_employees, db)
        
        await query.message.reply_text(
            "Выберите следующее действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании отчета. Попробуйте позже.",
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

