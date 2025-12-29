"""
Обработчики для формирования отчетов
"""
import asyncio
import os
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_REPORT_EMPLOYEE,
    SELECT_REPORT_PERIOD,
    ENTER_REPORT_CUSTOM_START,
    ENTER_REPORT_CUSTOM_END
)
from utils.keyboards import get_main_keyboard
from utils.helpers import run_in_thread
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)

DATE_INPUT_FORMAT = "%d.%m.%Y"
REPORT_MODE_EMPLOYEE = "employee"
REPORT_MODE_GLOBAL = "global"


def _parse_date_input(text: str):
    """Преобразовать строку в дату согласно формату ввода"""
    try:
        return datetime.strptime(text, DATE_INPUT_FORMAT)
    except ValueError:
        return None


def _start_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _end_of_day(dt: datetime) -> datetime:
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


async def _generate_report_for_period(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    db,
    period_name: str,
    start_date: datetime,
    end_date: datetime,
    query=None
) -> int:
    """Общая реализация формирования и отправки отчета"""
    report_mode = context.user_data.get('report_mode', REPORT_MODE_EMPLOYEE)
    emp_id = context.user_data.get('report_employee_id')
    message = update.effective_message
    
    employee = None
    if report_mode == REPORT_MODE_EMPLOYEE:
        if not emp_id:
            await message.reply_text(
                "❌ Сотрудник для отчета не выбран. Запустите формирование отчета заново.",
                reply_markup=get_main_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END

        employee = await run_in_thread(db.get_employee_by_id, emp_id)
        if not employee:
            await message.reply_text(
                "❌ Не удалось найти информацию о сотруднике. Попробуйте еще раз.",
                reply_markup=get_main_keyboard()
            )
            context.user_data.clear()
            return ConversationHandler.END
    
    if query:
        await query.edit_message_text("⏳ Формирую отчет, подождите...")
        target_message = query.message
    else:
        target_message = message
        await target_message.reply_text("⏳ Формирую отчет, подождите...")
    
    try:
        if report_mode == REPORT_MODE_EMPLOYEE:
            report_task = run_in_thread(
                db.get_employee_report,
                emp_id,
                start_date=start_date,
                end_date=end_date
            )
            movements_task = run_in_thread(
                db.get_employee_movements,
                emp_id,
                start_date,
                end_date
            )
            (connections, stats), movements = await asyncio.gather(report_task, movements_task)
        else:
            report_task = run_in_thread(
                db.get_global_report,
                start_date=start_date,
                end_date=end_date
            )
            connections, stats = await report_task
            movements = []
    except Exception as exc:
        logger.error(f"Ошибка при получении данных для отчета: {exc}")
        await target_message.reply_text(
            "❌ Не удалось получить данные. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if not connections and not movements:
        info_text = (
            f"ℹ️ У сотрудника <b>{employee['full_name']}</b> нет данных за период {period_name}."
            if report_mode == REPORT_MODE_EMPLOYEE
            else f"ℹ️ Нет подключений за период {period_name}."
        )
        await target_message.reply_text(
            info_text,
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    try:
        if report_mode == REPORT_MODE_EMPLOYEE:
            filename = await run_in_thread(
                ReportGenerator.generate_employee_report,
                employee_name=employee['full_name'],
                connections=connections,
                stats=stats,
                period_name=period_name,
                movements=movements
            )
        else:
            filename = await run_in_thread(
                ReportGenerator.generate_global_report,
                connections=connections,
                stats=stats,
                period_name=period_name,
            )
        
        with open(filename, 'rb') as file:
            caption = (
                f"📊 Отчет по сотруднику: <b>{employee['full_name']}</b>\n"
                f"Период: {period_name}\n"
                f"Подключений: {stats.get('total_connections', 0)}\n"
                f"ВОЛС всего: {stats.get('total_connection_fiber_meters', stats.get('total_fiber_meters', 0))} м\n"
                f"ВОЛС (на исполнителя): {stats.get('total_fiber_meters', 0)} м\n"
                f"Витая пара всего: {stats.get('total_connection_twisted_pair_meters', stats.get('total_twisted_pair_meters', 0))} м\n"
                f"Витая пара (на исполнителя): {stats.get('total_twisted_pair_meters', 0)} м"
            ) if report_mode == REPORT_MODE_EMPLOYEE else (
                f"📊 Общий отчет по подключениям\n"
                f"Период: {period_name}\n"
                f"Подключений: {stats.get('total_connections', 0)}\n"
                f"ВОЛС всего: {stats.get('total_connection_fiber_meters', stats.get('total_fiber_meters', 0))} м\n"
                f"ВОЛС (на исполнителя): {stats.get('total_fiber_meters', 0)} м\n"
                f"Витая пара всего: {stats.get('total_connection_twisted_pair_meters', stats.get('total_twisted_pair_meters', 0))} м\n"
                f"Витая пара (на исполнителя): {stats.get('total_twisted_pair_meters', 0)} м"
            )

            await target_message.reply_document(
                document=file,
                filename=filename,
                caption=caption,
                parse_mode='HTML'
            )
        
        os.remove(filename)
        
        await target_message.reply_text(
            "✅ Отчет сформирован!",
            reply_markup=get_main_keyboard()
        )
    except Exception as exc:
        logger.error(f"Ошибка при генерации отчета: {exc}")
        await target_message.reply_text(
            "❌ Ошибка при формировании отчета. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Начало формирования отчета"""
    employees = await run_in_thread(db.get_all_employees) or []
    
    if not employees:
        text = "⚠️ В системе нет ни одного сотрудника!"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("📑 Общий отчет (все сотрудники)", callback_data="rep_all")]]
    for emp in employees:
        keyboard.append([InlineKeyboardButton(emp['full_name'], callback_data=f"rep_emp_{emp['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='report_cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📊 <b>Сводный отчет</b>\n\nВыберите сотрудника:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return SELECT_REPORT_EMPLOYEE


async def report_select_period(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор периода для отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'report_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    if query.data == "rep_all":
        context.user_data['report_mode'] = REPORT_MODE_GLOBAL
        employee_name = "Все сотрудники"
    else:
        # Сохраняем выбранного сотрудника
        emp_id = int(query.data.split('_')[2])
        context.user_data['report_employee_id'] = emp_id
        context.user_data['report_mode'] = REPORT_MODE_EMPLOYEE
        
        employee = await run_in_thread(db.get_employee_by_id, emp_id)
        if not employee:
            await query.edit_message_text(
                "❌ Не удалось найти выбранного сотрудника. Попробуйте снова.",
                parse_mode='HTML'
            )
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END
        employee_name = employee['full_name']
    
    keyboard = [
        [InlineKeyboardButton("📅 Последняя неделя", callback_data='period_7')],
        [InlineKeyboardButton("📅 Последний месяц", callback_data='period_30')],
        [InlineKeyboardButton("📆 Выбрать диапазон", callback_data='period_custom')],
        [InlineKeyboardButton("❌ Отмена", callback_data='period_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Отчет по: <b>{employee_name}</b>\n\n"
        f"Выберите период для отчета:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_REPORT_PERIOD


async def report_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Генерация и отправка отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'period_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END
    
    if query.data == 'period_custom':
        context.user_data.pop('report_custom_start', None)
        await query.edit_message_text(
            "Введите начальную дату в формате <b>ДД.ММ.ГГГГ</b>\n"
            "Например: 01.09.2023",
            parse_mode='HTML'
        )
        return ENTER_REPORT_CUSTOM_START
    
    # Определяем период
    period_map = {
        'period_7': (7, 'Последняя неделя'),
        'period_30': (30, 'Последний месяц')
    }
    
    days, period_name = period_map[query.data]
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    return await _generate_report_for_period(
        update=update,
        context=context,
        db=db,
        period_name=period_name,
        start_date=start_date,
        end_date=end_date,
        query=query
    )


async def report_enter_custom_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение начальной даты пользовательского диапазона"""
    text = (update.message.text or "").strip()
    parsed_date = _parse_date_input(text)
    
    if not parsed_date:
        await update.message.reply_text(
            "❗️ Не удалось распознать дату. Используйте формат ДД.ММ.ГГГГ (например, 01.09.2023)."
        )
        return ENTER_REPORT_CUSTOM_START
    
    if parsed_date > datetime.now():
        await update.message.reply_text("Дата не может быть в будущем. Введите другую дату.")
        return ENTER_REPORT_CUSTOM_START
    
    context.user_data['report_custom_start'] = _start_of_day(parsed_date)
    
    await update.message.reply_text(
        "Теперь введите конечную дату в формате ДД.ММ.ГГГГ.\n"
        "Например: 30.09.2023"
    )
    return ENTER_REPORT_CUSTOM_END


async def report_enter_custom_end(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Получение конечной даты пользовательского диапазона и формирование отчета"""
    start_date = context.user_data.get('report_custom_start')
    
    if not start_date:
        await update.message.reply_text(
            "❗️ Начальная дата не задана. Пожалуйста, выберите период заново.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    text = (update.message.text or "").strip()
    parsed_date = _parse_date_input(text)
    
    if not parsed_date:
        await update.message.reply_text(
            "❗️ Не удалось распознать дату. Используйте формат ДД.ММ.ГГГГ (например, 30.09.2023)."
        )
        return ENTER_REPORT_CUSTOM_END
    
    if parsed_date > datetime.now():
        await update.message.reply_text("Дата не может быть в будущем. Введите другую дату.")
        return ENTER_REPORT_CUSTOM_END
    
    end_date = _end_of_day(parsed_date)
    
    if end_date < start_date:
        await update.message.reply_text("Конечная дата не может быть раньше начальной. Попробуйте снова.")
        return ENTER_REPORT_CUSTOM_END
    
    period_name = (
        f"{start_date.strftime('%d.%m.%Y')} - {parsed_date.strftime('%d.%m.%Y')}"
    )
    
    return await _generate_report_for_period(
        update=update,
        context=context,
        db=db,
        period_name=period_name,
        start_date=start_date,
        end_date=end_date
    )
