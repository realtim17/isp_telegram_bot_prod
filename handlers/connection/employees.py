"""
Обработчики выбора исполнителей для подключения
"""
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import SELECT_EMPLOYEES, logger
from utils.helpers import run_in_thread
from handlers.connection.ui import build_inline_keyboard


async def select_employee_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Переключение выбора сотрудника"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'employees_done':
        selected = context.user_data.get('selected_employees', [])
        
        if not selected:
            await query.answer("⚠️ Выберите хотя бы одного сотрудника!", show_alert=True)
            return SELECT_EMPLOYEES
        
        # Проверяем балансы и определяем, кто будет платить за материалы
        from handlers.connection.validation import check_materials_and_proceed
        return await check_materials_and_proceed(update, context, db)
    
    # Переключаем выбор сотрудника
    emp_id = int(query.data.split('_')[1])
    selected = context.user_data.get('selected_employees', [])
    
    if emp_id in selected:
        selected.remove(emp_id)
    else:
        selected.append(emp_id)
    
    context.user_data['selected_employees'] = selected
    
    # Обновляем клавиатуру
    employees = await run_in_thread(db.get_all_employees) or []
    keyboard = []
    
    for emp in employees:
        is_selected = emp['id'] in selected
        checkbox = "☑" if is_selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {emp['full_name']}", 
            callback_data=f"emp_{emp['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='employees_done')])
    reply_markup = build_inline_keyboard(keyboard)
    
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception:
        pass
    
    return SELECT_EMPLOYEES
