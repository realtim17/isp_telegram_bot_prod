"""
Пошаговый процесс выдачи ТМЦ сотруднику (аналог «Нового подключения»)
"""
from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    TMC_SELECT_EMPLOYEE,
    TMC_ENTER_FIBER,
    TMC_ENTER_TWISTED,
    TMC_SELECT_ROUTER,
    TMC_ENTER_ROUTER_QTY,
    TMC_SELECT_SNR,
    TMC_ENTER_SNR_QTY,
    TMC_SELECT_ONU,
    TMC_ENTER_ONU_QTY,
    TMC_SELECT_MEDIA,
    TMC_ENTER_MEDIA_QTY,
    TMC_SELECT_SFP,
    TMC_ENTER_SFP_QTY,
    TMC_COMMENT,
    TMC_CONFIRM,
)
from utils.helpers import run_in_thread
from utils.keyboards import get_main_keyboard

if TYPE_CHECKING:  # pragma: no cover - используется только для типов
    from .flow import EmployeeFlow


SKIP_TEXT = "⏭️ Пропустить"
CANCEL_TEXT = "❌ Отмена"
TOTAL_STEPS = 9

STEP_INFO: Dict[str, tuple[int, str, str]] = {
    "fiber": (1, "ВОЛС", "🧵"),
    "twisted": (2, "Витая пара", "🪢"),
    "router": (3, "Роутеры", "📡"),
    "snr": (4, "SNR оптические боксы", "🧰"),
    "onu": (5, "ONU абонентские терминалы", "🔌"),
    "media": (6, "Медиаконверторы", "🔄"),
    "sfp": (7, "SFP модули", "🧿"),
    "comment": (8, "Комментарий к выдаче", "📝"),
    "confirm": (9, "Подтверждение операции", "✅"),
}

EQUIPMENT_SPEC: Dict[str, Dict[str, object]] = {
    "router": {
        "button_prefix": "tmc_router",
        "all_names_method": "get_all_router_names",
        "employee_items_method": "get_employee_routers",
        "name_field": "router_name",
        "data_key": "router",
        "select_state": TMC_SELECT_ROUTER,
        "quantity_state": TMC_ENTER_ROUTER_QTY,
        "next_step": "snr",
        "noun": "модель роутера",
        "quantity_noun": "количество роутеров",
        "add_method": "add_router_to_employee",
    },
    "snr": {
        "button_prefix": "tmc_snr",
        "all_names_method": "get_all_snr_box_names",
        "employee_items_method": "get_employee_snr_boxes",
        "name_field": "box_name",
        "data_key": "snr",
        "select_state": TMC_SELECT_SNR,
        "quantity_state": TMC_ENTER_SNR_QTY,
        "next_step": "onu",
        "noun": "модель SNR бокса",
        "quantity_noun": "количество боксов",
        "add_method": "add_snr_box_to_employee",
    },
    "onu": {
        "button_prefix": "tmc_onu",
        "all_names_method": "get_all_onu_names",
        "employee_items_method": "get_employee_onu",
        "name_field": "device_name",
        "data_key": "onu",
        "select_state": TMC_SELECT_ONU,
        "quantity_state": TMC_ENTER_ONU_QTY,
        "next_step": "media",
        "noun": "модель ONU",
        "quantity_noun": "количество ONU",
        "add_method": "add_onu_to_employee",
    },
    "media": {
        "button_prefix": "tmc_media",
        "all_names_method": "get_all_media_converter_names",
        "employee_items_method": "get_employee_media_converters",
        "name_field": "device_name",
        "data_key": "media",
        "select_state": TMC_SELECT_MEDIA,
        "quantity_state": TMC_ENTER_MEDIA_QTY,
        "next_step": "sfp",
        "noun": "модель медиаконвертора",
        "quantity_noun": "количество медиаконверторов",
        "add_method": "add_media_converter_to_employee",
    },
    "sfp": {
        "button_prefix": "tmc_sfp",
        "all_names_method": "get_all_sfp_module_names",
        "employee_items_method": "get_employee_sfp_modules",
        "name_field": "module_name",
        "data_key": "sfp",
        "select_state": TMC_SELECT_SFP,
        "quantity_state": TMC_ENTER_SFP_QTY,
        "next_step": "comment",
        "noun": "модель SFP",
        "quantity_noun": "количество SFP модулей",
        "add_method": "add_sfp_module_to_employee",
    },
}


def _default_tmc_data() -> Dict[str, object]:
    return {
        "employee_id": None,
        "fiber": 0.0,
        "twisted": 0.0,
        "router": {"model": "-", "qty": 0},
        "snr": {"model": "-", "qty": 0},
        "onu": {"model": "-", "qty": 0},
        "media": {"model": "-", "qty": 0},
        "sfp": {"model": "-", "qty": 0},
        "comment": "",
    }


def _step_title(step_key: str) -> str:
    number, title, emoji = STEP_INFO.get(step_key, (0, "", ""))
    return f"{emoji} <b>Шаг {number}/{TOTAL_STEPS}: {title}</b>"


def _reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[SKIP_TEXT, CANCEL_TEXT]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def _clear_tmc_context(context: ContextTypes.DEFAULT_TYPE, keep_employee: bool = False) -> None:
    """Удалить временные данные процесса выдачи."""
    employee = context.user_data.get("tmc_employee") if keep_employee else None
    context.user_data.pop("tmc_data", None)
    context.user_data.pop("tmc_manual_target", None)
    context.user_data.pop("tmc_active_select_state", None)
    context.user_data.pop("tmc_employee", None)
    if keep_employee and employee:
        context.user_data["tmc_employee"] = employee


def _get_tmc_data(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, object]:
    data = context.user_data.get("tmc_data")
    if not isinstance(data, dict):
        data = _default_tmc_data()
        context.user_data["tmc_data"] = data
    return data


async def start_issue_flow(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запустить выбор сотрудника перед пошаговым процессом выдачи."""
    query = update.callback_query
    await query.answer()

    employees = await run_in_thread(flow.db.get_all_employees)
    if not employees:
        await query.edit_message_text("⚠️ В системе нет сотрудников.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    _clear_tmc_context(context)

    keyboard = []
    for emp in employees:
        fiber = emp.get("fiber_balance", 0) or 0
        twisted = emp.get("twisted_pair_balance", 0) or 0
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"👤 {emp['full_name']} (ВОЛС {fiber}м / ВП {twisted}м)",
                    callback_data=f"tmc_emp_{emp['id']}",
                )
            ]
        )
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="tmc_back_to_menu")])
    keyboard.append([InlineKeyboardButton(CANCEL_TEXT, callback_data="tmc_cancel")])

    await query.edit_message_text(
        "📦 <b>Выдача ТМЦ</b>\n\nВыберите сотрудника:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return TMC_SELECT_EMPLOYEE


async def select_employee(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Фиксируем выбранного сотрудника и просим данные по ВОЛС."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "tmc_cancel":
        return await _cancel_from_query(flow, query, context)

    if data == "tmc_back_to_menu":
        from .start import return_to_manage_menu

        _clear_tmc_context(context)
        return await return_to_manage_menu(flow, update, context)

    if not data.startswith("tmc_emp_"):
        return TMC_SELECT_EMPLOYEE

    emp_id = int(data.split("_")[-1])
    employee = await run_in_thread(flow.db.get_employee_by_id, emp_id)
    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    context.user_data["tmc_employee"] = employee
    tmc_data = _default_tmc_data()
    tmc_data["employee_id"] = emp_id
    context.user_data["tmc_data"] = tmc_data

    await query.edit_message_text(
        "✅ Сотрудник выбран. Начинаем выдачу ТМЦ.",
        parse_mode="HTML",
    )
    return await _prompt_fiber_step(query.message, context)


async def enter_fiber(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка шага с вводом ВОЛС."""
    message = update.message
    text = (message.text or "").strip()

    if text == CANCEL_TEXT:
        return await _cancel_from_message(flow, message, context)

    tmc_data = _get_tmc_data(context)

    if text == SKIP_TEXT:
        tmc_data["fiber"] = 0
        await message.reply_text(
            f"{_step_title('fiber')}\n\n⏭️ Пропущено.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await _prompt_twisted_step(message, context)

    try:
        fiber_value = float(text.replace(",", "."))
        if fiber_value < 0:
            raise ValueError
    except ValueError:
        await message.reply_text("⚠️ Введите корректное неотрицательное число (например, 120 или 45.5).")
        return TMC_ENTER_FIBER

    tmc_data["fiber"] = fiber_value
    await message.reply_text(
        f"{_step_title('fiber')}\n\n✅ Запланировано к выдаче: {fiber_value} м.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return await _prompt_twisted_step(message, context)


async def enter_twisted(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка шага с вводом витой пары."""
    message = update.message
    text = (message.text or "").strip()

    if text == CANCEL_TEXT:
        return await _cancel_from_message(flow, message, context)

    tmc_data = _get_tmc_data(context)

    if text == SKIP_TEXT:
        tmc_data["twisted"] = 0
        await message.reply_text(
            f"{_step_title('twisted')}\n\n⏭️ Пропущено.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await _prompt_equipment_step(flow, message, context, "router")

    try:
        twisted_value = float(text.replace(",", "."))
        if twisted_value < 0:
            raise ValueError
    except ValueError:
        await message.reply_text("⚠️ Введите корректное неотрицательное число (например, 120 или 45.5).")
        return TMC_ENTER_TWISTED

    tmc_data["twisted"] = twisted_value
    await message.reply_text(
        f"{_step_title('twisted')}\n\n✅ Запланировано к выдаче: {twisted_value} м.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return await _prompt_equipment_step(flow, message, context, "router")


async def manual_model_input(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода модели вручную."""
    message = update.message
    manual_key = context.user_data.get("tmc_manual_target")
    spec = EQUIPMENT_SPEC.get(manual_key)
    if not spec:
        current_state = context.user_data.get("tmc_active_select_state", TMC_SELECT_ROUTER)
        await message.reply_text("Используйте кнопки для выбора модели.", reply_markup=ReplyKeyboardRemove())
        return current_state

    text = (message.text or "").strip()
    if text == CANCEL_TEXT:
        return await _cancel_from_message(flow, message, context)

    if text == SKIP_TEXT:
        context.user_data["tmc_manual_target"] = None
        slot = _get_equipment_slot(context, manual_key)
        slot["model"] = "-"
        slot["qty"] = 0
        await message.reply_text(
            f"{_step_title(manual_key)}\n\n⏭️ Пропущено.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await _go_to_next_step(flow, message, context, spec["next_step"])

    if not text:
        await message.reply_text("⚠️ Название модели не может быть пустым. Повторите ввод или нажмите «Пропустить».")
        return spec["select_state"]

    context.user_data["tmc_manual_target"] = None
    slot = _get_equipment_slot(context, manual_key)
    slot["model"] = text

    await message.reply_text(
        f"{_step_title(manual_key)}\n\n✅ Модель: <b>{text}</b>\n\nУкажите {spec['quantity_noun']} (шт.) "
        "или нажмите «Пропустить».",
        parse_mode="HTML",
        reply_markup=_reply_keyboard(),
    )
    return spec["quantity_state"]


async def select_router(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_equipment_callback(flow, update, context, "router")


async def select_snr(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_equipment_callback(flow, update, context, "snr")


async def select_onu(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_equipment_callback(flow, update, context, "onu")


async def select_media(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_equipment_callback(flow, update, context, "media")


async def select_sfp(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_equipment_callback(flow, update, context, "sfp")


async def enter_router_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_quantity_input(flow, update, context, "router")


async def enter_snr_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_quantity_input(flow, update, context, "snr")


async def enter_onu_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_quantity_input(flow, update, context, "onu")


async def enter_media_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_quantity_input(flow, update, context, "media")


async def enter_sfp_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_quantity_input(flow, update, context, "sfp")


async def enter_comment(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Финальный текстовый шаг."""
    message = update.message
    text = (message.text or "").strip()

    if text == CANCEL_TEXT:
        return await _cancel_from_message(flow, message, context)

    if text == SKIP_TEXT:
        _get_tmc_data(context)["comment"] = ""
        await message.reply_text(
            f"{_step_title('comment')}\n\n⏭️ Без комментария.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await _show_confirmation(message, context)

    _get_tmc_data(context)["comment"] = text
    await message.reply_text(
        f"{_step_title('comment')}\n\n📝 Сохранено: {text}",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return await _show_confirmation(message, context)


async def confirm_operation(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение или повторное прохождение процесса."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "tmc_cancel":
        return await _cancel_from_query(flow, query, context)

    if data == "tmc_restart":
        employee = context.user_data.get("tmc_employee")
        if not employee:
            await query.edit_message_text("⚠️ Сотрудник не найден, перезапустите процесс.")
            return ConversationHandler.END
        _clear_tmc_context(context, keep_employee=True)
        tmc_data = _default_tmc_data()
        tmc_data["employee_id"] = employee.get("id")
        context.user_data["tmc_data"] = tmc_data
        await query.edit_message_text("🔁 Начинаем заполнение заново.")
        return await _prompt_fiber_step(query.message, context)

    if data != "tmc_confirm":
        return TMC_CONFIRM

    employee = context.user_data.get("tmc_employee") or {}
    employee_id = employee.get("id")
    if not employee_id:
        await query.edit_message_text("⚠️ Сотрудник не найден. Завершите процесс и начните заново.")
        return ConversationHandler.END

    tmc_data = _get_tmc_data(context)
    created_by = query.from_user.id if query.from_user else None
    comment = tmc_data.get("comment", "")
    errors: List[str] = []

    if tmc_data.get("fiber", 0) > 0 or tmc_data.get("twisted", 0) > 0:
        success = await run_in_thread(
            flow.db.add_material_to_employee,
            employee_id,
            tmc_data.get("fiber", 0),
            tmc_data.get("twisted", 0),
            created_by,
            comment,
        )
        if not success:
            errors.append("материалы")

    for key, spec in EQUIPMENT_SPEC.items():
        slot = _get_equipment_slot(context, key)
        model = slot.get("model") or "-"
        qty = slot.get("qty", 0) or 0
        if not model or model == "-" or qty <= 0:
            continue
        method_name = spec["add_method"]
        add_method = getattr(flow.db, method_name, None)
        if not add_method:
            errors.append(key)
            continue
        success = await run_in_thread(add_method, employee_id, model, qty, created_by, comment)
        if not success:
            errors.append(key)

    if errors:
        await query.edit_message_text(
            "⚠️ Не удалось записать позиции: " + ", ".join(errors),
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(
            "✅ Выдача ТМЦ завершена.",
            parse_mode="HTML",
        )
    _clear_tmc_context(context)
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# --- Вспомогательные функции ---


async def _prompt_fiber_step(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    employee = context.user_data.get("tmc_employee") or {}
    fiber_balance = employee.get("fiber_balance", 0) or 0
    await message.reply_text(
        f"{_step_title('fiber')}\n\n"
        f"📊 Текущий баланс: {fiber_balance} м\n"
        "Введите количество метров ВОЛС к выдаче или нажмите «Пропустить».",
        parse_mode="HTML",
        reply_markup=_reply_keyboard(),
    )
    return TMC_ENTER_FIBER


async def _prompt_twisted_step(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    employee = context.user_data.get("tmc_employee") or {}
    twisted_balance = employee.get("twisted_pair_balance", 0) or 0
    await message.reply_text(
        f"{_step_title('twisted')}\n\n"
        f"📊 Текущий баланс: {twisted_balance} м\n"
        "Введите количество метров витой пары или нажмите «Пропустить».",
        parse_mode="HTML",
        reply_markup=_reply_keyboard(),
    )
    return TMC_ENTER_TWISTED


async def _prompt_equipment_step(flow: "EmployeeFlow", message, context: ContextTypes.DEFAULT_TYPE, key: str) -> int:
    spec = EQUIPMENT_SPEC[key]
    context.user_data["tmc_active_select_state"] = spec["select_state"]
    employee = context.user_data.get("tmc_employee") or {}
    employee_id = employee.get("id")
    if not employee_id:
        await message.reply_text("⚠️ Сотрудник не найден, завершите процесс.")
        return ConversationHandler.END

    all_names = await run_in_thread(getattr(flow.db, spec["all_names_method"])) or []
    employee_items = await run_in_thread(getattr(flow.db, spec["employee_items_method"]), employee_id) or []
    counts = {item.get(spec["name_field"]): item.get("quantity", 0) or 0 for item in employee_items}

    keyboard_rows = []
    for model_name in all_names:
        qty = counts.get(model_name, 0)
        qty_text = f"{qty} шт." if qty else "0 шт."
        keyboard_rows.append(
            [InlineKeyboardButton(f"{model_name} ({qty_text})", callback_data=f"{spec['button_prefix']}_model_{model_name}")]
        )
    keyboard_rows.append([InlineKeyboardButton("✏️ Ввести вручную", callback_data=f"{spec['button_prefix']}_manual")])
    keyboard_rows.append([InlineKeyboardButton(SKIP_TEXT, callback_data=f"{spec['button_prefix']}_skip")])
    keyboard_rows.append([InlineKeyboardButton(CANCEL_TEXT, callback_data="tmc_cancel")])

    if all_names:
        prompt = "Выберите модель из списка или воспользуйтесь ручным вводом:"
    else:
        prompt = (
            "⚠️ В системе пока нет сохранённых моделей. Введите название вручную или пропустите шаг:"
        )

    await message.reply_text(
        f"{_step_title(key)}\n\n{prompt}",
        reply_markup=InlineKeyboardMarkup(keyboard_rows),
        parse_mode="HTML",
    )
    return spec["select_state"]


async def _handle_equipment_callback(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> int:
    query = update.callback_query
    await query.answer()

    spec = EQUIPMENT_SPEC[key]
    prefix = spec["button_prefix"]
    data = query.data

    if data == "tmc_cancel":
        return await _cancel_from_query(flow, query, context)

    if data == f"{prefix}_skip":
        slot = _get_equipment_slot(context, key)
        slot["model"] = "-"
        slot["qty"] = 0
        await query.edit_message_text(
            f"{_step_title(key)}\n\n⏭️ Пропущено.",
            parse_mode="HTML",
        )
        return await _go_to_next_step(flow, query.message, context, spec["next_step"])

    if data == f"{prefix}_manual":
        context.user_data["tmc_manual_target"] = key
        await query.edit_message_text(
            f"{_step_title(key)}\n\n✏️ Введите {spec['noun']} текстом:",
            parse_mode="HTML",
        )
        await query.message.reply_text(
            "Отправьте название сообщением или нажмите «Пропустить».",
            reply_markup=_reply_keyboard(),
        )
        return spec["select_state"]

    if data.startswith(f"{prefix}_model_"):
        model_name = data.replace(f"{prefix}_model_", "", 1)
        slot = _get_equipment_slot(context, key)
        slot["model"] = model_name
        await query.edit_message_text(
            f"{_step_title(key)}\n\n✅ Выбрано: <b>{model_name}</b>",
            parse_mode="HTML",
        )
        await query.message.reply_text(
            f"Укажите {spec['quantity_noun']} (шт.) или нажмите «Пропустить».",
            reply_markup=_reply_keyboard(),
        )
        return spec["quantity_state"]

    return spec["select_state"]


async def _handle_quantity_input(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE, key: str) -> int:
    message = update.message
    text = (message.text or "").strip()
    spec = EQUIPMENT_SPEC[key]

    if text == CANCEL_TEXT:
        return await _cancel_from_message(flow, message, context)

    if text == SKIP_TEXT:
        slot = _get_equipment_slot(context, key)
        slot["model"] = "-"
        slot["qty"] = 0
        await message.reply_text(
            f"{_step_title(key)}\n\n⏭️ Пропущено.",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return await _go_to_next_step(flow, message, context, spec["next_step"])

    try:
        quantity = int(text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await message.reply_text("⚠️ Введите целое положительное число или нажмите «Пропустить».")
        return spec["quantity_state"]

    slot = _get_equipment_slot(context, key)
    slot["qty"] = quantity
    await message.reply_text(
        f"{_step_title(key)}\n\n✅ {spec['quantity_noun'].capitalize()}: {quantity} шт.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )
    return await _go_to_next_step(flow, message, context, spec["next_step"])


async def _prompt_comment(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    await message.reply_text(
        f"{_step_title('comment')}\n\nВведите комментарий к выдаче или нажмите «Пропустить».",
        parse_mode="HTML",
        reply_markup=_reply_keyboard(),
    )
    return TMC_COMMENT


async def _show_confirmation(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    employee = context.user_data.get("tmc_employee") or {}
    tmc_data = _get_tmc_data(context)

    def format_slot(slot: Dict[str, object]) -> str:
        model = slot.get("model") or "-"
        qty = slot.get("qty", 0) or 0
        if not model or model == "-" or qty <= 0:
            return "—"
        return f"{model} x{qty}"

    summary = (
        f"{_step_title('confirm')}\n\n"
        f"👤 Сотрудник: <b>{employee.get('full_name', '—')}</b>\n\n"
        f"📏 ВОЛС: {tmc_data.get('fiber', 0)} м\n"
        f"🪢 Витая пара: {tmc_data.get('twisted', 0)} м\n"
        f"📡 Роутеры: {format_slot(tmc_data.get('router', {}))}\n"
        f"🧰 SNR боксы: {format_slot(tmc_data.get('snr', {}))}\n"
        f"🔌 ONU: {format_slot(tmc_data.get('onu', {}))}\n"
        f"🔄 Медиаконверторы: {format_slot(tmc_data.get('media', {}))}\n"
        f"🧿 SFP: {format_slot(tmc_data.get('sfp', {}))}\n"
        f"📝 Комментарий: {tmc_data.get('comment') or '—'}\n\n"
        "Подтвердить операцию?"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Подтвердить", callback_data="tmc_confirm")],
            [InlineKeyboardButton("🔁 Заполнить заново", callback_data="tmc_restart")],
            [InlineKeyboardButton("❌ Отмена", callback_data="tmc_cancel")],
        ]
    )

    await message.reply_text(summary, reply_markup=keyboard, parse_mode="HTML")
    return TMC_CONFIRM


def _get_equipment_slot(context: ContextTypes.DEFAULT_TYPE, key: str) -> Dict[str, object]:
    data = _get_tmc_data(context)
    slot = data.get(key)
    if not isinstance(slot, dict):
        slot = {"model": "-", "qty": 0}
        data[key] = slot
    return slot


async def _go_to_next_step(flow: "EmployeeFlow", message, context: ContextTypes.DEFAULT_TYPE, next_step: str) -> int:
    if next_step == "comment":
        return await _prompt_comment(message, context)
    return await _prompt_equipment_step(flow, message, context, next_step)


async def _cancel_from_query(flow: "EmployeeFlow", query, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear_tmc_context(context)
    await query.edit_message_text("❌ Выдача ТМЦ отменена.")
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


async def _cancel_from_message(flow: "EmployeeFlow", message, context: ContextTypes.DEFAULT_TYPE) -> int:
    _clear_tmc_context(context)
    await message.reply_text(
        "❌ Выдача ТМЦ отменена.",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END
