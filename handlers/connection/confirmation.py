"""
Подтверждение данных и сохранение подключения
"""
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import CONFIRM, CONNECTION_TYPES, logger
from utils.keyboards import get_main_keyboard
from utils.helpers import send_connection_report, run_in_thread, _format_report_text


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Показать подтверждение перед сохранением"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    
    # Получаем подробности по выбранным сотрудникам (параллельно)
    employee_rows = []
    if selected_employees:
        employee_rows = await asyncio.gather(
            *(run_in_thread(db.get_employee_by_id, emp_id) for emp_id in selected_employees)
        )
    employee_map = {
        emp_id: emp for emp_id, emp in zip(selected_employees, employee_rows) if emp
    }
    employee_names = [
        employee_map[emp_id]['full_name']
        for emp_id in selected_employees
        if emp_id in employee_map
    ]
    
    # Получаем читаемое название типа подключения
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    # Рассчитываем долю на каждого
    emp_count = len(selected_employees)
    fiber_per_emp = round(data['fiber_meters'] / max(emp_count, 1), 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / max(emp_count, 1), 2)
    
    # Единый материально ответственный для всех списаний
    material_payer_id = context.user_data.get('material_payer_id')
    if not material_payer_id and selected_employees:
        material_payer_id = selected_employees[0]
        context.user_data['material_payer_id'] = material_payer_id
    router_payer_id = material_payer_id
    snr_box_payer_id = material_payer_id
    onu_payer_id = material_payer_id
    media_payer_id = material_payer_id
    sfp_payer_id = material_payer_id
    context.user_data['router_payer_id'] = router_payer_id
    context.user_data['snr_box_payer_id'] = snr_box_payer_id
    context.user_data['onu_payer_id'] = onu_payer_id
    context.user_data['media_payer_id'] = media_payer_id
    context.user_data['sfp_payer_id'] = sfp_payer_id
    
    payer_info = ""
    if material_payer_id:
        payer = employee_map.get(material_payer_id)
        if not payer:
            payer = await run_in_thread(db.get_employee_by_id, material_payer_id)
            if payer:
                employee_map[material_payer_id] = payer
        if payer:
            payer_info += f"\n\n💰 <b>Материалы списываются с:</b> {payer['full_name']}"
    
    if router_payer_id:
        router_payer = employee_map.get(router_payer_id)
        if not router_payer:
            router_payer = await run_in_thread(db.get_employee_by_id, router_payer_id)
            if router_payer:
                employee_map[router_payer_id] = router_payer
        if router_payer:
            router_quantity = data.get('router_quantity', 1)
            quantity_text = f" ({router_quantity} шт.)" if router_quantity > 1 else ""
            payer_info += f"\n📡 <b>Роутер списывается с:</b> {router_payer['full_name']}{quantity_text}"
    
    if snr_box_payer_id:
        snr_payer = employee_map.get(snr_box_payer_id)
        if not snr_payer:
            snr_payer = await run_in_thread(db.get_employee_by_id, snr_box_payer_id)
            if snr_payer:
                employee_map[snr_box_payer_id] = snr_payer
        if snr_payer:
            qty = data.get('snr_box_quantity', 0) or 0
            quantity_text = f" ({int(qty)} шт.)" if qty else ""
            payer_info += f"\n🧰 <b>SNR бокс списывается с:</b> {snr_payer['full_name']}{quantity_text}"

    onu_payer_id = context.user_data.get('onu_payer_id')
    media_payer_id = context.user_data.get('media_payer_id')
    sfp_payer_id = context.user_data.get('sfp_payer_id')

    if onu_payer_id:
        onu_payer = employee_map.get(onu_payer_id)
        if not onu_payer:
            onu_payer = await run_in_thread(db.get_employee_by_id, onu_payer_id)
            if onu_payer:
                employee_map[onu_payer_id] = onu_payer
        if onu_payer:
            onu_quantity = data.get('onu_quantity', 0) or 0
            quantity_text = f" ({int(onu_quantity)} шт.)" if onu_quantity else ""
            payer_info += f"\n🔌 <b>ONU списываются с:</b> {onu_payer['full_name']}{quantity_text}"

    if media_payer_id:
        media_payer = employee_map.get(media_payer_id)
        if not media_payer:
            media_payer = await run_in_thread(db.get_employee_by_id, media_payer_id)
            if media_payer:
                employee_map[media_payer_id] = media_payer
        if media_payer:
            media_quantity = data.get('media_converter_quantity', 0) or 0
            quantity_text = f" ({int(media_quantity)} шт.)" if media_quantity else ""
            payer_info += f"\n🔄 <b>Медиаконверторы списываются с:</b> {media_payer['full_name']}{quantity_text}"

    if sfp_payer_id:
        sfp_payer = employee_map.get(sfp_payer_id)
        if not sfp_payer:
            sfp_payer = await run_in_thread(db.get_employee_by_id, sfp_payer_id)
            if sfp_payer:
                employee_map[sfp_payer_id] = sfp_payer
        if sfp_payer:
            sfp_quantity = data.get('sfp_module_quantity', 0) or 0
            quantity_text = f" ({int(sfp_quantity)} шт.)" if sfp_quantity else ""
            payer_info += f"\n🧿 <b>SFP модули списываются с:</b> {sfp_payer['full_name']}{quantity_text}"
    
    # Формируем отображение роутера
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    snr_box_model = data.get('snr_box_model', '-') or '-'
    snr_box_quantity = data.get('snr_box_quantity', 0) or 0
    onu_model = data.get('onu_model', '-') or '-'
    onu_quantity = data.get('onu_quantity', 0) or 0
    media_model = data.get('media_converter_model', '-') or '-'
    media_quantity = data.get('media_converter_quantity', 0) or 0
    sfp_model = data.get('sfp_module_model', '-') or '-'
    sfp_quantity = data.get('sfp_module_quantity', 0) or 0
    
    if router_model == '-' or not router_model:
        router_display = "-"
    else:
        router_display = router_model
        if router_quantity > 1:
            router_display += f" ({router_quantity} шт.)"
    
    snr_display = "-"
    if snr_box_model and snr_box_model != '-':
        snr_display = snr_box_model
        if snr_box_quantity > 0:
            snr_display += f" ({snr_box_quantity} шт.)"
    
    if onu_model == '-' or not onu_model:
        onu_display = "-"
    else:
        onu_display = onu_model
        if onu_quantity > 0:
            onu_display += f" ({onu_quantity} шт.)"
    
    if media_model == '-' or not media_model:
        media_display = "-"
    else:
        media_display = media_model
        if media_quantity > 0:
            media_display += f" ({media_quantity} шт.)"
    
    # Формируем отображение порта
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подтверждено" if contract_signed else "⏭️ Пропущено"
    
    # Получаем информацию о доступе на роутер
    router_access = data.get('router_access', False)
    router_access_status = "✅ Получен" if router_access else "⏭️ Пропущено"
    
    # Получаем информацию о Телеграмм Боте
    telegram_bot_connected = data.get('telegram_bot_connected', False)
    telegram_bot_status = "✅ Подключен" if telegram_bot_connected else "-"
    comment_text = data.get('comment') or "-"
    
    report_preview = _format_report_text("ПРЕДПРОСМОТР", data, employee_names).strip()
    confirmation_text = (
        f"{report_preview}{payer_info}"
        f"\n\n📸 Фото: {len(photos)} шт."
        f"\n\nВсё верно? Подтвердите создание отчета."
    )
    
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


async def confirm_connection(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Подтверждение и сохранение подключения"""
    query = update.callback_query
    await query.answer()
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
        router_payer_id = context.user_data.get('router_payer_id')
        snr_box_payer_id = context.user_data.get('snr_box_payer_id')
        onu_payer_id = context.user_data.get('onu_payer_id')
        media_payer_id = context.user_data.get('media_payer_id')
        sfp_payer_id = context.user_data.get('sfp_payer_id')
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
                twisted_pair_meters=data['twisted_pair_meters'],
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
    except Exception as exc:
        logger.exception("Ошибка при подтверждении подключения: %s", exc)
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Произошла ошибка при сохранении подключения. Попробуйте начать заново.",
            parse_mode='HTML'
        )
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
