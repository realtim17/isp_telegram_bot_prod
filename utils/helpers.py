"""
Вспомогательные функции
"""
from typing import Dict, List, Any
from datetime import datetime
import logging
import asyncio
from functools import partial

from telegram import InputMediaPhoto, Update

from config import (
    REPORTS_CHANNEL_ID,
    CONNECTION_TYPES,
    ACCESS_DENIED_MESSAGE,
)
from utils.access import AccessManager

logger = logging.getLogger(__name__)


async def run_in_thread(func, *args, **kwargs) -> Any:
    """Выполнить блокирующую функцию в отдельном потоке"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args, **kwargs))


def _create_media_group(photos: List[str], caption: str) -> List[InputMediaPhoto]:
    """Создать медиа-группу из фотографий с подписью"""
    media_group = []
    for idx, photo_id in enumerate(photos):
        if idx == 0:
            media_group.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode='HTML'))
        else:
            media_group.append(InputMediaPhoto(media=photo_id))
    return media_group


def _format_qty(value: float | int | None, unit: str = "шт.") -> str:
    """Форматирование количества в удобный вид."""
    if not value:
        return "-"
    number = float(value)
    if number.is_integer():
        value_str = str(int(number))
    else:
        value_str = str(round(number, 2))
    return f"{value_str} {unit}"


def _format_report_text(
    connection_id: int | str,
    data: Dict,
    employee_names: List[str],
    payer_names: Dict[str, str] | None = None,
    show_payers: bool = True,
) -> str:
    """Форматировать текст отчёта"""
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    is_magistral = conn_type == 'magistral'
    type_display = f"🪢 {type_name}" if is_magistral else type_name
    
    emp_count = max(len(employee_names), 1)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    # Получаем информацию о роутерах (если есть)
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    snr_model = data.get('snr_box_model', '-') or '-'
    snr_quantity = data.get('snr_box_quantity', 0) or 0
    onu_model = data.get('onu_model', '-') or '-'
    onu_quantity = data.get('onu_quantity', 0) or 0
    media_model = data.get('media_converter_model', '-') or '-'
    media_quantity = data.get('media_converter_quantity', 0) or 0
    sfp_model = data.get('sfp_module_model', '-') or '-'
    sfp_quantity = data.get('sfp_module_quantity', 0) or 0
    
    # Если роутер пропущен или "-", отображаем "-"
    if router_model == '-' or not router_model:
        router_info = "-"
    else:
        router_info = router_model
    if router_quantity > 1:
        router_info += f" ({router_quantity} шт.)"
    
    if snr_model == '-' or not snr_model:
        snr_info = "-"
    else:
        snr_info = snr_model
        if snr_quantity > 0:
            snr_info += f" ({snr_quantity} шт.)"
    
    if onu_model == '-' or not onu_model:
        onu_info = "-"
    else:
        onu_info = onu_model
        if onu_quantity > 0:
            onu_info += f" ({onu_quantity} шт.)"
    
    if media_model == '-' or not media_model:
        media_info = "-"
    else:
        media_info = media_model
        if media_quantity > 0:
            media_info += f" ({media_quantity} шт.)"

    if sfp_model == '-' or not sfp_model:
        sfp_info = "-"
    else:
        sfp_info = sfp_model
        if sfp_quantity > 0:
            sfp_info += f" ({sfp_quantity} шт.)"
    
    # Получаем информацию о порте
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подтверждено" if contract_signed else "⏭️ Пропущено"
    
    # Получаем информацию о доступе на роутер
    router_access = data.get('router_access', False)
    router_access_status = "✅ Получен" if router_access else "⏭️ Пропущено"
    
    comment_text = data.get('comment') or "-"
    telegram_bot_connected = data.get('telegram_bot_connected', False)
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
        twisted_total = float(data.get('twisted_pair_meters', 0) or 0)
        if payer_names.get('fiber') and fiber_total > 0:
            payer_lines.append(f"  • ВОЛС: {payer_names['fiber']}")
        if payer_names.get('twisted') and twisted_total > 0:
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
    ]
    if hooks_total or is_magistral:
        per_employee_lines.append(f"  • Крюки: {hooks_per_emp_display}")
    if ork_total or is_magistral:
        per_employee_lines.append(f"  • ОРК / ОРШ: {ork_per_emp_display}")
    if mufta_total or is_magistral:
        per_employee_lines.append(f"  • Муфты: {mufta_per_emp_display}")

    payer_block = f"\n\n{payer_section}" if payer_section else ""

    return f"""
<b>📋 ОТЧЕТ О ПОДКЛЮЧЕНИИ #{connection_id}</b>

{info_block}

<b>📝 Комментарий:</b> {comment_text}

<b>📏 Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

<b>👥 Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

<b>💡 Расчет на каждого исполнителя:</b>
{chr(10).join(per_employee_lines)}{payer_block}

<b>📅 Дата подключения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""


async def send_connection_report(message, connection_id: int, data: Dict, photos: List[str], 
                                 employee_ids: List[int], db, payer_ids: Dict[str, int] | None = None) -> None:
    """Отправить красиво отформатированный отчет о подключении с фотографиями"""
    try:
        # Получаем имена сотрудников
        employees = (await run_in_thread(db.get_all_employees)) or []
        employee_map = {emp['id']: emp['full_name'] for emp in employees}
        employee_names = [employee_map[emp_id] for emp_id in employee_ids if emp_id in employee_map]
        payer_names = None
        if payer_ids:
            payer_names = {
                key: employee_map[emp_id]
                for key, emp_id in payer_ids.items()
                if emp_id and emp_id in employee_map
            } or None
        
        # Формируем текст отчета
        report_text = _format_report_text(
            connection_id,
            data,
            employee_names,
            payer_names,
            show_payers=False
        )
        
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


async def ensure_user_authorized(update: Update, access_manager: AccessManager | None = None) -> bool:
    """Проверить, есть ли у пользователя доступ к боту"""
    user = update.effective_user
    if not user or not access_manager:
        return True
    if access_manager.is_allowed(user.id):
        return True
    await _notify_access_denied(update)
    logger.info("Доступ запрещен для пользователя ID %s", user.id)
    return False


async def _notify_access_denied(update: Update) -> None:
    """Отправить сообщение об отсутствии доступа"""
    query = update.callback_query
    message = update.effective_message
    
    if query:
        try:
            await query.answer("⛔ Нет доступа", show_alert=True)
        except Exception as exc:
            logger.debug("Не удалось отправить alert об отказе доступа: %s", exc)
    
    if message:
        await message.reply_text(ACCESS_DENIED_MESSAGE)
    else:
        logger.warning("Получен апдейт без message для уведомления об отказе доступа")
