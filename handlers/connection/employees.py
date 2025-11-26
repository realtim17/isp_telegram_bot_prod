"""
Обработчики выбора исполнителей для подключения
"""
from typing import Optional

from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from config import SELECT_EMPLOYEES
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread
from handlers.connection.ui import build_inline_keyboard


async def start_employee_selection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    pre_text: Optional[str] = None
) -> int:
    """Показать шаг выбора исполнителей"""
    query = update.callback_query
    message = update.effective_message

    employees = await run_in_thread(db.get_all_employees) or []
    if not employees:
        if query:
            await query.edit_message_text(
                "⚠️ В системе нет ни одного сотрудника!\n\n"
                "Обратитесь к администратору для добавления сотрудников.",
                reply_markup=None
            )
            await query.message.reply_text(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.reply_text(
                "⚠️ В системе нет ни одного сотрудника!\n\n"
                "Обратитесь к администратору для добавления сотрудников.",
                reply_markup=get_main_keyboard()
            )
        return ConversationHandler.END
    
    context.user_data['selected_employees'] = []
    keyboard = [
        [InlineKeyboardButton(f"☐ {emp['full_name']}", callback_data=f"emp_{emp['id']}")]
        for emp in employees
    ]
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='employees_done')])
    reply_markup = build_inline_keyboard(keyboard)
    
    message_parts = []
    if pre_text:
        message_parts.append(pre_text)
    message_parts.append(
        "👥 <b>Шаг 15/15: Выбор исполнителей</b>\n\n"
        "Выберите сотрудников, которые участвовали в подключении:\n"
        "(можно выбрать нескольких)"
    )
    message_text = "\n\n".join(message_parts)
    
    if query:
        await query.edit_message_text(
            message_text,
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "Нажмите ✅ Готово после выбора:",
            reply_markup=reply_markup
        )
    else:
        await message.reply_text(
            message_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    
    return SELECT_EMPLOYEES


async def select_employee_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Переключение выбора сотрудника"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'employees_done':
        selected = context.user_data.get('selected_employees', [])
        
        if not selected:
            await query.answer("⚠️ Выберите хотя бы одного сотрудника!", show_alert=True)
            return SELECT_EMPLOYEES
        
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
