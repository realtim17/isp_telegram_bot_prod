"""
Вспомогательные функции
"""
from typing import Dict, List
from datetime import datetime
import logging

from telegram import InputMediaPhoto

from config import REPORTS_CHANNEL_ID, CONNECTION_TYPES

logger = logging.getLogger(__name__)


def _create_media_group(photos: List[str], caption: str) -> List[InputMediaPhoto]:
    """Создать медиа-группу из фотографий с подписью"""
    media_group = []
    for idx, photo_id in enumerate(photos):
        if idx == 0:
            media_group.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode='HTML'))
        else:
            media_group.append(InputMediaPhoto(media=photo_id))
    return media_group


def _format_report_text(connection_id: int, data: Dict, employee_names: List[str]) -> str:
    """Форматировать текст отчёта"""
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    emp_count = len(employee_names)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_external_total = float(data.get('twisted_pair_external_meters', 0) or 0)
    twisted_internal_total = float(data.get('twisted_pair_internal_meters', 0) or 0)
    twisted_total = float(data.get('twisted_pair_meters', 0) or 0)
    if twisted_external_total == 0 and twisted_internal_total == 0 and twisted_total > 0:
        twisted_external_total = round(twisted_total / 2, 2)
        twisted_internal_total = round(twisted_total - twisted_external_total, 2)
    elif twisted_total == 0 and (twisted_external_total or twisted_internal_total):
        twisted_total = twisted_external_total + twisted_internal_total
    twisted_per_emp = round(twisted_total / emp_count, 2)
    twisted_external_per_emp = round(twisted_external_total / emp_count, 2)
    twisted_internal_per_emp = round(twisted_internal_total / emp_count, 2)
    
    # Получаем информацию о роутерах (если есть)
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    
    # Если роутер пропущен или "-", отображаем "-"
    if router_model == '-' or not router_model:
        router_info = "-"
    else:
        router_info = router_model
    if router_quantity > 1:
        router_info += f" ({router_quantity} шт.)"
    
    # Получаем информацию о порте
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    account_number = str(data.get('account_number') or "-")
    bitrix_task_url = data.get('bitrix_task_url') or "-"
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подписан" if contract_signed else "❌ Не подписан"
    
    # Получаем информацию о доступе на роутер
    router_access = data.get('router_access', False)
    router_access_status = "✅ Получен" if router_access else "⏭️ Пропущено"
    
    # Получаем информацию о Телеграмм Боте
    telegram_bot_connected = data.get('telegram_bot_connected', False)
<<<<<<< Updated upstream
    telegram_bot_status = "✅ Подключен" if telegram_bot_connected else "-"
    
=======
    telegram_bot_status = "✅ Подключен" if telegram_bot_connected else "⏭️ Пропущено"
    hooks_total = float(data.get('hooks_quantity', 0) or 0)
    ork_total = float(data.get('ork_quantity', 0) or 0)
    mufta_total = float(data.get('mufta_quantity', 0) or 0)
    hooks_display = _format_qty(hooks_total)
    ork_display = _format_qty(ork_total)
    mufta_display = _format_qty(mufta_total)
    hooks_per_emp_display = _format_qty(hooks_total / emp_count if hooks_total else 0)
    ork_per_emp_display = _format_qty(ork_total / emp_count if ork_total else 0)
    mufta_per_emp_display = _format_qty(mufta_total / emp_count if mufta_total else 0)

    payer_section = ""
    if show_payers and payer_names:
        payer_lines = []
        fiber_total = float(data.get('fiber_meters', 0) or 0)
        if payer_names.get('fiber') and fiber_total > 0:
            payer_lines.append(f"  • ВОЛС: {payer_names['fiber']}")
        if payer_names.get('twisted_external') and twisted_external_total > 0:
            payer_lines.append(f"  • Внеш. витая пара: {payer_names['twisted_external']}")
        if payer_names.get('twisted_internal') and twisted_internal_total > 0:
            payer_lines.append(f"  • Внут. витая пара: {payer_names['twisted_internal']}")
        if payer_names.get('twisted') and twisted_total > 0 and not (
            payer_names.get('twisted_external') or payer_names.get('twisted_internal')
        ):
            payer_lines.append(f"  • Витая пара: {payer_names['twisted']}")
        if payer_names.get('router') and router_model and router_model != '-' and router_quantity:
            payer_lines.append(f"  • Роутеры: {payer_names['router']}")
        if payer_names.get('snr') and snr_model and snr_model != '-' and snr_quantity:
            payer_lines.append(f"  • SNR боксы: {payer_names['snr']}")
        if payer_names.get('onu') and onu_model and onu_model != '-' and onu_quantity:
            payer_lines.append(f"  • ONU: {payer_names['onu']}")
        if payer_names.get('media') and media_model and media_model != '-' and media_quantity:
            payer_lines.append(f"  • Медиаконверторы: {payer_names['media']}")
        if payer_names.get('sfp') and sfp_model and sfp_model != '-' and sfp_quantity:
            payer_lines.append(f"  • SFP модули: {payer_names['sfp']}")
        if payer_lines:
            payer_section = "<b>💰 МОЛ:</b>\n" + "\n".join(payer_lines)

    if is_magistral:
        info_block = "\n".join([
            f"<b>📍 Адрес:</b> <code>{data['address']}</code>",
            f"<b>🏢 Тип подключения:</b> {type_display}",
            f"<b> SFP модуль:</b> {sfp_info}",
            f"<b>🪝 Крюки:</b> {hooks_display}",
            f"<b>🔩 ОРК / ОРШ:</b> {ork_display}",
            f"<b>🧰 Муфты:</b> {mufta_display}",
        ])
    else:
        info_block = "\n".join([
            f"<b>📍 Адрес:</b> <code>{data['address']}</code>",
            f"<b>🏢 Тип подключения:</b> {type_display}",
            f"<b>🔢 Лицевой счет:</b> {account_number}",
            f"<b>🔗 Bitrix24:</b> {bitrix_task_url}",
            f"<b> Модель роутера:</b> {router_info}",
            f"<b> SNR бокс:</b> {snr_info}",
            f"<b> ONU абон.терминал:</b> {onu_info}",
            f"<b> Медиаконвертор:</b> {media_info}",
            f"<b> SFP модуль:</b> {sfp_info}",
            f"<b>🔌 Номер порта:</b> {port_display}",
            f"<b>🔑 Доступ на роутер:</b> {router_access_status}",
            f"<b>📄 Договор:</b> {contract_status}",
            f"<b>🤖 Телеграмм Бот:</b> {telegram_bot_status}",
        ])
    
    per_employee_lines = [
        f"  • ВОЛС: {fiber_per_emp} м",
        f"  • Витая пара: {twisted_per_emp} м",
        f"  • Внеш. витая пара: {twisted_external_per_emp} м",
        f"  • Внут. витая пара: {twisted_internal_per_emp} м",
    ]
    if hooks_total or is_magistral:
        per_employee_lines.append(f"  • Крюки: {hooks_per_emp_display}")
    if ork_total or is_magistral:
        per_employee_lines.append(f"  • ОРК / ОРШ: {ork_per_emp_display}")
    if mufta_total or is_magistral:
        per_employee_lines.append(f"  • Муфты: {mufta_per_emp_display}")

    payer_block = f"\n\n{payer_section}" if payer_section else ""

>>>>>>> Stashed changes
    return f"""
<b>📋 ОТЧЕТ О ПОДКЛЮЧЕНИИ #{connection_id}</b>

<b>📍 Адрес:</b> {data['address']}
<b> Тип подключения:</b> {type_name}
<b> Модель роутера:</b> {router_info}
<b> Доступ на роутер:</b> {router_access_status}
<b> Договор:</b> {contract_status}
<b> Телеграмм Бот:</b> {telegram_bot_status}
<b> Порт:</b> {port_display}

<b>📏 Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {twisted_total} м
  • Внеш. витая пара: {twisted_external_total} м
  • Внут. витая пара: {twisted_internal_total} м

<b>👥 Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

<b>💡 Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м

<b>📅 Дата подключения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""


async def send_connection_report(message, connection_id: int, data: Dict, photos: List[str], 
                                 employee_ids: List[int], db) -> None:
    """Отправить красиво отформатированный отчет о подключении с фотографиями"""
    try:
        # Получаем имена сотрудников
        employees = db.get_all_employees()
        employee_names = [emp['full_name'] for emp in employees if emp['id'] in employee_ids]
        
        # Формируем текст отчета
        report_text = _format_report_text(connection_id, data, employee_names)
        
        # Отправляем отчет пользователю
        if photos:
            media_group = _create_media_group(photos, report_text)
            await message.reply_media_group(media=media_group)
            logger.info(f"Отправлен отчет #{connection_id} пользователю с {len(photos)} фото")
        else:
            await message.reply_text(report_text, parse_mode='HTML')
            logger.info(f"Отправлен отчет #{connection_id} пользователю без фото")
        
        # Отправляем отчет в канал, если он настроен
        if REPORTS_CHANNEL_ID:
            try:
                bot = message.get_bot()
                if photos:
                    media_group = _create_media_group(photos, report_text)
                    await bot.send_media_group(chat_id=REPORTS_CHANNEL_ID, media=media_group)
                    logger.info(f"Отчет #{connection_id} отправлен в канал с {len(photos)} фото")
                else:
                    await bot.send_message(chat_id=REPORTS_CHANNEL_ID, text=report_text, parse_mode='HTML')
                    logger.info(f"Отчет #{connection_id} отправлен в канал без фото")
            except Exception as channel_error:
                logger.error(f"Ошибка при отправке отчета в канал: {channel_error}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета о подключении: {e}")
        await message.reply_text(
            "⚠️ Отчет создан, но возникла ошибка при отправке фотографий.",
            parse_mode='HTML'
        )

