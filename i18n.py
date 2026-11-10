"""Bot interface texts in English (default) and Russian.

Only the chat interface is translated; the Excel template and the PDF stay as they are.
To add a language: add a dict to TEXTS and LABELS and a button to LANGUAGES.
"""
import fields as F

DEFAULT_LANG = "en"
LANGUAGES = {"en": "🇬🇧 English", "ru": "🇷🇺 Русский"}

TEXTS = {
    "en": {
        # reply keyboard
        "btn_new": "➕ New flight",
        "btn_list": "📋 My flights",
        "btn_name": "👤 My name",
        "btn_lang": "🌐 Language",
        "btn_skip": "⏭ Skip",
        "btn_clear": "🗑 Clear",
        "btn_cancel": "❌ Cancel",
        "btn_nil": "🚫 NIL",
        "btn_dash": "➖ Long dash",
        "btn_no_infants": "👶 No infants",
        # inline buttons
        "b_header": "🧾 Header",
        "b_docs": "📑 Documents",
        "b_timeline": "⏱ Timeline",
        "b_remarks": "📝 Remarks",
        "b_pdf": "📄 Generate PDF",
        "b_delete": "🗑 Delete",
        "b_my_flights": "⬅️ My flights",
        "b_back": "⬅️ Back",
        "b_default": "⚡ Apply default",
        "b_now": "🕒 Now",
        "b_enter_time": "✏️ Enter time",
        "b_part_now_1": "▶️ {part} now",
        "b_part_now_2": "⏹ {part} now",
        "b_write_remarks": "✏️ Write remarks",
        "b_clear": "🗑 Clear",
        "b_dash": "➖ Long dash",
        "b_yes_delete": "🗑 Yes, delete",
        # start / name / language
        "welcome": "👋 Welcome! Send your <b>full name</b>. It is printed as the signature on your PDFs.",
        "choose_lang_hint": "🌐 You can switch the language below.",
        "hi": "👋 Hi, {name}!",
        "name_current": "Current name: <b>{name}</b>\nSend a new name:",
        "name_first": "Please send your full name first (used as signature).",
        "name_len": "Name must be 2-40 characters.",
        "name_saved": "✅ Saved: <b>{name}</b>",
        "choose_lang": "🌐 Choose language:",
        "lang_set": "✅ Language: English",
        "cancelled": "Cancelled.",
        "use_menu": "Use the menu below 👇",
        # wizard / editing
        "step": "Step {n}/{total}",
        "today": "Today",
        "tomorrow": "Tomorrow",
        "date_prompt_extra": "Pick today / tomorrow or type a date.",
        "invalid": "⚠️ Invalid value. Expected: {hint}",
        "invalid_time": "⚠️ Invalid time. Expected: {hint}",
        "flight_created": "✅ Flight created. Fill the rest from the card below.",
        "current": "Current: <b>{value}</b>",
        "field_saved": "✅ {label}: {value}",
        "time_saved": "✅ Saved {value}",
        "infants_q": "👶 <b>{label}: {pax}</b>\nAny infants? Tap a number or “No infants”.",
        # lists / card
        "no_flights": "No flights yet. Tap “➕ New flight”.",
        "your_flights": "📋 <b>Your flights</b> (kept for 3 days):",
        "not_found": "Flight not found (deleted or older than 3 days).",
        "stand": "Stand",
        "card_docs": "📑 Documents",
        "card_timeline": "⏱ Timeline",
        "card_remarks": "📝 Remarks",
        "yes": "yes",
        "header_title": "🧾 <b>Header</b>\nTap a field to change it.",
        "docs_text": "📑 <b>Documents</b>\nTap to cycle: ✅ YES → ❌ NO → ➖ N/A → ▫️ empty",
        "default_applied": "Default applied",
        "timeline_text": "⏱ <b>Timeline</b> (Tashkent time)\nTap an event, then “now” to stamp the current time.",
        "time_label": "Time",
        "time_prompt": "⏱ <b>{label}</b>\nSend time as HHMM, e.g. 0750",
        "cleared": "Cleared",
        "remarks_title": "📝 <b>Remarks/Irregularities</b>",
        "remarks_prompt": "📝 Send remarks text (max {max} characters).",
        "remarks_long": "⚠️ Too long ({n}). Max {max} characters, it must fit the form.",
        "remarks_saved": "✅ Remarks saved.",
        "generating": "Generating PDF…",
        "delete_q": "Delete flight <b>{flight}</b>?",
        "deleted": "🗑 Deleted.",
        # hints by value kind / field
        "hint_date": "dd.mm.yy, e.g. 07.11.26",
        "hint_time": "HHMM, e.g. 0750",
        "hint_station": "3-letter code, e.g. LED",
        "hint_flight": "e.g. HY742/741",
        "hint_int": "a number, e.g. 167",
        "hint_pax": "a number, e.g. 167, or 167+3 with 3 infants",
        "hint_infants": "number of infants, e.g. 3",
        "hint_text": "free text, 1-40 characters",
        "hint_ac": "type/registration, e.g. A320/32091",
        "hint_cgo_in": "kg/pieces, e.g. 350kg/12pcs",
        "hint_cgo_out": "kg/pieces, e.g. 420kg/15pcs",
        "hint_bag_in": "kg/pieces, e.g. 2568kg/149pcs",
        "hint_bag_out": "kg/pieces, e.g. 2387kg/125pcs",
    },
    "ru": {
        "btn_new": "➕ Новый рейс",
        "btn_list": "📋 Мои рейсы",
        "btn_name": "👤 Моё имя",
        "btn_lang": "🌐 Язык",
        "btn_skip": "⏭ Пропустить",
        "btn_clear": "🗑 Очистить",
        "btn_cancel": "❌ Отмена",
        "btn_nil": "🚫 NIL",
        "btn_dash": "➖ Длинное тире",
        "btn_no_infants": "👶 Без младенцев",
        "b_header": "🧾 Заголовок",
        "b_docs": "📑 Документы",
        "b_timeline": "⏱ Хронометраж",
        "b_remarks": "📝 Замечания",
        "b_pdf": "📄 Создать PDF",
        "b_delete": "🗑 Удалить",
        "b_my_flights": "⬅️ Мои рейсы",
        "b_back": "⬅️ Назад",
        "b_default": "⚡ По умолчанию",
        "b_now": "🕒 Сейчас",
        "b_enter_time": "✏️ Ввести время",
        "b_part_now_1": "▶️ {part} сейчас",
        "b_part_now_2": "⏹ {part} сейчас",
        "b_write_remarks": "✏️ Написать замечания",
        "b_clear": "🗑 Очистить",
        "b_dash": "➖ Длинное тире",
        "b_yes_delete": "🗑 Да, удалить",
        "welcome": "👋 Добро пожаловать! Отправьте ваши <b>имя и фамилию</b>. Они печатаются как подпись в PDF.",
        "choose_lang_hint": "🌐 Язык можно сменить ниже.",
        "hi": "👋 Здравствуйте, {name}!",
        "name_current": "Текущее имя: <b>{name}</b>\nОтправьте новое имя:",
        "name_first": "Сначала отправьте ваши имя и фамилию (используются как подпись).",
        "name_len": "Имя должно быть от 2 до 40 символов.",
        "name_saved": "✅ Сохранено: <b>{name}</b>",
        "choose_lang": "🌐 Выберите язык:",
        "lang_set": "✅ Язык: русский",
        "cancelled": "Отменено.",
        "use_menu": "Используйте меню ниже 👇",
        "step": "Шаг {n}/{total}",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        "date_prompt_extra": "Выберите сегодня / завтра или введите дату.",
        "invalid": "⚠️ Неверное значение. Ожидается: {hint}",
        "invalid_time": "⚠️ Неверное время. Ожидается: {hint}",
        "flight_created": "✅ Рейс создан. Остальное заполните в карточке ниже.",
        "current": "Сейчас: <b>{value}</b>",
        "field_saved": "✅ {label}: {value}",
        "time_saved": "✅ Сохранено {value}",
        "infants_q": "👶 <b>{label}: {pax}</b>\nЕсть младенцы? Выберите число или «Без младенцев».",
        "no_flights": "Рейсов пока нет. Нажмите «➕ Новый рейс».",
        "your_flights": "📋 <b>Ваши рейсы</b> (хранятся 3 дня):",
        "not_found": "Рейс не найден (удалён или старше 3 дней).",
        "stand": "Стоянка",
        "card_docs": "📑 Документы",
        "card_timeline": "⏱ Хронометраж",
        "card_remarks": "📝 Замечания",
        "yes": "есть",
        "header_title": "🧾 <b>Заголовок</b>\nНажмите на поле, чтобы изменить.",
        "docs_text": "📑 <b>Документы</b>\nНажимайте по кругу: ✅ ДА → ❌ НЕТ → ➖ Н/П → ▫️ пусто",
        "default_applied": "Применено по умолчанию",
        "timeline_text": "⏱ <b>Хронометраж</b> (время Ташкента)\nВыберите операцию, затем «сейчас», чтобы отметить текущее время.",
        "time_label": "Время",
        "time_prompt": "⏱ <b>{label}</b>\nОтправьте время в формате ЧЧММ, напр. 0750",
        "cleared": "Очищено",
        "remarks_title": "📝 <b>Замечания/нарушения</b>",
        "remarks_prompt": "📝 Отправьте текст замечаний (макс. {max} символов).",
        "remarks_long": "⚠️ Слишком длинно ({n}). Максимум {max} символов, текст должен поместиться в форму.",
        "remarks_saved": "✅ Замечания сохранены.",
        "generating": "Создаю PDF…",
        "delete_q": "Удалить рейс <b>{flight}</b>?",
        "deleted": "🗑 Удалено.",
        "hint_date": "дд.мм.гг, напр. 07.11.26",
        "hint_time": "ЧЧММ, напр. 0750",
        "hint_station": "код из 3 букв латиницей, напр. LED",
        "hint_flight": "напр. HY742/741",
        "hint_int": "число, напр. 167",
        "hint_pax": "число, напр. 167, или 167+3 с 3 младенцами",
        "hint_infants": "число младенцев, напр. 3",
        "hint_text": "произвольный текст, 1-40 символов",
        "hint_ac": "тип/регистрация, напр. A320/32091",
        "hint_cgo_in": "кг/места, напр. 350kg/12pcs",
        "hint_cgo_out": "кг/места, напр. 420kg/15pcs",
        "hint_bag_in": "кг/места, напр. 2568kg/149pcs",
        "hint_bag_out": "кг/места, напр. 2387kg/125pcs",
    },
}

# Field / checklist / event names. English comes from fields.py.
LABELS = {
    "ru": {
        # header
        "date": "Дата", "from_st": "Откуда", "to_st": "Куда", "flight": "Номер рейса",
        "ac": "Тип/регистрация", "sta": "STA (прибытие)", "park": "Место стоянки",
        "std": "STD (вылет)", "delay": "Задержка", "pax_in": "Пасс. прилёт",
        "pax_out": "Пасс. вылет", "trs": "Трансфер", "cgo_in": "Груз прилёт",
        "cgo_out": "Груз вылет",
        "bag_in": "Багаж прилёт", "bag_out": "Багаж вылет",
        # checklist
        "cover": "Чек лист", "service": "Форма по услугам", "loadsheet": "Загрузочная ведомость",
        "tripinfo": "Трип инфо", "lir": "Схема загрузки (LIR)", "paxman": "Пасс. манифест",
        "bagman": "Багажная ведомость", "bingo": "Реестр баг. ведомости", "fuel": "Документы по топливу",
        "workorder": "Карта наряда", "messages": "Сообщения", "techlog": "Тех. журнал ВС",
        "incident": "Инциденты/нарушения", "deicing": "Противообледенение", "cargoman": "Грузовой манифест",
        "journeylog": "Бортовой журнал", "dgr": "Опасные грузы (DGR/NOTOC)",
        # timeline
        "equipment": "Оборудование на месте", "ata": "ATA / On block", "stairs": "Трап / телетрап",
        "door_open": "Дверь открыта", "deboard": "Высадка пассажиров", "unload": "Выгрузка багажа",
        "avsec": "Досмотр АБ", "cleaning": "Уборка", "catering": "Кейтеринг", "fueling": "Заправка",
        "toilet": "Обслуживание туалетов", "water": "Заправка водой", "ready": "Готов к посадке",
        "boarding": "Посадка пассажиров", "loading": "Загрузка багажа", "door_closed": "Дверь закрыта",
        "offblock": "Off block", "pushback": "Буксировка (pushback)", "takeoff": "Взлёт",
        # start/finish parts
        "part_Start": "Начало", "part_Finish": "Окончание", "part_ATA": "ATA", "part_On block": "On block",
    },
}

_EN_LABELS = {
    **{k: v[0] for k, v in F.HEADER.items()},
    **dict(F.CHECKLIST),
    **{k: label for k, label, _ in F.EVENTS},
}


def norm(lang: str | None) -> str:
    return lang if lang in TEXTS else DEFAULT_LANG


def t(lang: str, key: str, **kw) -> str:
    text = TEXTS[norm(lang)].get(key) or TEXTS[DEFAULT_LANG].get(key) or key
    return text.format(**kw) if kw else text


def label(lang: str, key: str) -> str:
    """Name of a header field, checklist item or timeline event."""
    return LABELS.get(norm(lang), {}).get(key) or _EN_LABELS.get(key, key)


def part(lang: str, name: str) -> str:
    """'Start' / 'Finish' / 'ATA' / 'On block'."""
    return LABELS.get(norm(lang), {}).get(f"part_{name}") or name


def hint(lang: str, kind: str, key: str | None = None) -> str:
    if key and f"hint_{key}" in TEXTS[DEFAULT_LANG]:
        return t(lang, f"hint_{key}")
    return t(lang, f"hint_{kind}")


def all_variants(key: str) -> set[str]:
    """A button text in every language, for matching reply-keyboard presses."""
    return {TEXTS[lang][key] for lang in TEXTS}
