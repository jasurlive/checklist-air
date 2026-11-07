"""Message texts and keyboards (in the user's language, see i18n.py)."""
from html import escape

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import fields as F
from i18n import LANGUAGES, hint, label, part, t


class Cb(CallbackData, prefix="f"):
    """Inline button payload. a=action, id=flight id, k=field/item/event/lang, w=1|2."""
    a: str
    id: int = 0
    k: str = ""
    w: int = 0


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for key in ("btn_new", "btn_list", "btn_name", "btn_lang"):
        kb.button(text=t(lang, key))
    kb.adjust(2, 2)
    return kb.as_markup(resize_keyboard=True)


def input_menu(lang: str, suggestions: list[str], skip: bool = False, clear: bool = False) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for s in suggestions:
        kb.button(text=s)
    extra = (["btn_skip"] if skip else []) + (["btn_clear"] if clear else []) + ["btn_cancel"]
    for e in extra:
        kb.button(text=t(lang, e))
    kb.adjust(*([2] * ((len(suggestions) + 1) // 2)), len(extra))
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def lang_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for code, name in LANGUAGES.items():
        kb.button(text=name, callback_data=Cb(a="lang", k=code))
    kb.adjust(len(LANGUAGES))
    return kb.as_markup()


# --- dates ---------------------------------------------------------------------
def date_buttons(lang: str) -> list[str]:
    """['07.11.26 · Today', '08.11.26 · Tomorrow'] (Tashkent time)."""
    today, tomorrow = F.date_suggestions()
    return [f"{today} · {t(lang, 'today')}", f"{tomorrow} · {t(lang, 'tomorrow')}"]


def strip_button_suffix(text: str) -> str:
    """'07.11.26 · Today' -> '07.11.26' (typed dates pass through unchanged)."""
    return text.split(" · ", 1)[0]


def prompt_for(lang: str, key: str) -> str:
    kind = F.HEADER[key][2]
    text = f"<b>{label(lang, key)}</b>\n<i>{hint(lang, kind, key)}</i>"
    if kind == "date":
        text += f"\n{t(lang, 'date_prompt_extra')}"
    return text


# --- flight card ---------------------------------------------------------------
def _v(flight, key) -> str:
    return escape(flight.get(key) or "—")


def card_text(lang: str, flight: dict, checks: dict, times: dict) -> str:
    done_times = sum(1 for t1, t2 in times.values() if t1 or t2)
    return (
        f"✈️ <b>{_v(flight, 'flight')}</b>  ·  {_v(flight, 'date')}\n"
        f"{_v(flight, 'from_st')} → {_v(flight, 'to_st')}  ·  {_v(flight, 'ac')}  ·  "
        f"{t(lang, 'stand')} {_v(flight, 'park')}\n"
        f"STA {_v(flight, 'sta')}  ·  STD {_v(flight, 'std')}\n"
        f"PAX {_v(flight, 'pax_in')} / {_v(flight, 'pax_out')}\n\n"
        f"{t(lang, 'card_docs')}: {len(checks)}/{len(F.CHECKLIST)}\n"
        f"{t(lang, 'card_timeline')}: {done_times}/{len(F.EVENTS)}\n"
        f"{t(lang, 'card_remarks')}: {t(lang, 'yes') if flight.get('remarks') else '—'}"
    )


def card_kb(lang: str, fid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for text_key, action in (("b_header", "hdr"), ("b_docs", "docs"), ("b_timeline", "tl"),
                             ("b_remarks", "rem"), ("b_pdf", "pdf"), ("b_delete", "del")):
        kb.button(text=t(lang, text_key), callback_data=Cb(a=action, id=fid))
    kb.button(text=t(lang, "b_my_flights"), callback_data=Cb(a="list"))
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def back_btn(kb: InlineKeyboardBuilder, lang: str, fid: int, action: str = "card"):
    kb.button(text=t(lang, "b_back"), callback_data=Cb(a=action, id=fid))


def flights_kb(flights: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for f in flights:
        kb.button(text=f"✈️ {f['flight'] or '?'}  ·  {f['date'] or ''}", callback_data=Cb(a="card", id=f["id"]))
    kb.adjust(1)
    return kb.as_markup()


def header_kb(lang: str, flight: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key in F.HEADER:
        kb.button(text=f"{label(lang, key)}: {flight.get(key) or '—'}",
                  callback_data=Cb(a="hset", id=flight["id"], k=key))
    back_btn(kb, lang, flight["id"])
    kb.adjust(2)
    return kb.as_markup()


def docs_kb(lang: str, fid: int, checks: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, _ in F.CHECKLIST:
        kb.button(text=f"{F.CHECK_ICONS[checks.get(key)]} {label(lang, key)}", callback_data=Cb(a="chk", id=fid, k=key))
    kb.button(text=t(lang, "b_default"), callback_data=Cb(a="chkdef", id=fid))
    back_btn(kb, lang, fid)
    kb.adjust(2)
    return kb.as_markup()


def timeline_kb(lang: str, fid: int, times: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, _, pair in F.EVENTS:
        t1, t2 = times.get(key, (None, None))
        if pair:
            val = f"{t1 or '····'}–{t2 or '····'}" if (t1 or t2) else "—"
        else:
            val = t1 or "—"
        mark = "✅" if (t1 and (t2 or not pair)) else ("🕓" if (t1 or t2) else "▫️")
        kb.button(text=f"{mark} {label(lang, key)}: {val}", callback_data=Cb(a="ev", id=fid, k=key))
    back_btn(kb, lang, fid)
    kb.adjust(1)
    return kb.as_markup()


def event_text(lang: str, key: str, times: dict) -> str:
    _, pair = F.EVENT_BY_KEY[key]
    t1, t2 = times.get(key, (None, None))
    if pair:
        return (f"⏱ <b>{label(lang, key)}</b>\n{part(lang, pair[0])}: {t1 or '—'}\n"
                f"{part(lang, pair[1])}: {t2 or '—'}")
    return f"⏱ <b>{label(lang, key)}</b>\n{t(lang, 'time_label')}: {t1 or '—'}"


def event_kb(lang: str, fid: int, key: str) -> InlineKeyboardMarkup:
    _, pair = F.EVENT_BY_KEY[key]
    kb = InlineKeyboardBuilder()
    if pair:
        p1, p2 = part(lang, pair[0]), part(lang, pair[1])
        kb.button(text=t(lang, "b_part_now_1", part=p1), callback_data=Cb(a="now", id=fid, k=key, w=1))
        kb.button(text=t(lang, "b_part_now_2", part=p2), callback_data=Cb(a="now", id=fid, k=key, w=2))
        kb.button(text=f"✏️ {p1}", callback_data=Cb(a="tset", id=fid, k=key, w=1))
        kb.button(text=f"✏️ {p2}", callback_data=Cb(a="tset", id=fid, k=key, w=2))
    else:
        kb.button(text=t(lang, "b_now"), callback_data=Cb(a="now", id=fid, k=key, w=1))
        kb.button(text=t(lang, "b_enter_time"), callback_data=Cb(a="tset", id=fid, k=key, w=1))
    kb.button(text=t(lang, "b_clear"), callback_data=Cb(a="tclr", id=fid, k=key))
    back_btn(kb, lang, fid, action="tl")
    kb.adjust(2)
    return kb.as_markup()


def remarks_text(lang: str, remarks: str | None) -> str:
    return f"{t(lang, 'remarks_title')}\n{escape(remarks or '—')}"


def remarks_kb(lang: str, fid: int, has: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "b_write_remarks"), callback_data=Cb(a="remset", id=fid))
    if has:
        kb.button(text=t(lang, "b_clear"), callback_data=Cb(a="remclr", id=fid))
    back_btn(kb, lang, fid)
    kb.adjust(1)
    return kb.as_markup()


def confirm_delete_kb(lang: str, fid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t(lang, "b_yes_delete"), callback_data=Cb(a="delok", id=fid))
    back_btn(kb, lang, fid)
    return kb.as_markup()
