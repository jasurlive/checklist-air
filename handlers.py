"""All bot interactions. Every flight lookup is scoped to the user who created it."""
import asyncio
from html import escape

from aiogram import F as Filter
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message

import fields as F
import views as V
from db import Database
from i18n import LANGUAGES, all_variants, hint, label, norm, part, t
from pdf import build_pdf

router = Router()


@router.message.outer_middleware()
@router.callback_query.outer_middleware()
async def user_context(handler, event, data):
    """Inject `lang` and `user_name` (None until registered) into every handler."""
    user = data.get("event_from_user")
    name, lang = await data["db"].get_user(user.id) if user else (None, "en")
    data["lang"], data["user_name"] = norm(lang), name
    return await handler(event, data)


def btn(key: str):
    """Filter: a reply-keyboard button pressed, in any language."""
    return Filter.text.in_(all_variants(key))


class St(StatesGroup):
    name = State()       # asking for the user's name (signature)
    wizard = State()     # new-flight header wizard
    field = State()      # editing one header field
    time = State()       # typing a time manually
    remarks = State()    # typing remarks
    infants = State()    # asking for infants after a PAX number


# --- helpers ---------------------------------------------------------------------
async def safe_edit(cq: CallbackQuery, text: str, markup=None):
    try:
        await cq.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e):
            raise


async def load(db: Database, fid: int, uid: int):
    flight = await db.get_flight(fid, uid)
    if not flight:
        return None, None, None
    return flight, await db.get_checks(fid), await db.get_times(fid)


async def send_card(msg: Message, db: Database, lang: str, fid: int, uid: int):
    flight, checks, times = await load(db, fid, uid)
    if flight:
        await msg.answer(V.card_text(lang, flight, checks, times), reply_markup=V.card_kb(lang, fid))


async def back_to_menu(msg: Message, state: FSMContext, lang: str, text: str):
    await state.clear()
    await msg.answer(text, reply_markup=V.main_menu(lang))


async def require_name(msg: Message, state: FSMContext, lang: str, user_name: str | None) -> bool:
    if user_name:
        return True
    await state.set_state(St.name)
    await msg.answer(t(lang, "name_first"))
    return False


def parse_input(kind: str, text: str) -> str:
    if kind == "date":
        text = V.strip_button_suffix(text)
    return F.parse_value(kind, text)


def suggestions_for(lang: str, key: str, recent: list[str]) -> list[str]:
    return V.date_buttons(lang) if F.HEADER[key][2] == "date" else recent


# --- start / name / language ---------------------------------------------------------
@router.message(CommandStart())
async def start(msg: Message, state: FSMContext, lang: str, user_name: str | None):
    await state.clear()
    if not user_name:
        await state.set_state(St.name)
        await msg.answer(f"{t(lang, 'welcome')}\n\n{t(lang, 'choose_lang_hint')}", reply_markup=V.lang_kb())
        return
    await msg.answer(t(lang, "hi", name=escape(user_name)), reply_markup=V.main_menu(lang))


@router.message(btn("btn_lang"))
@router.message(Command("lang"))
async def ask_lang(msg: Message, lang: str):
    await msg.answer(t(lang, "choose_lang"), reply_markup=V.lang_kb())


@router.callback_query(V.Cb.filter(Filter.a == "lang"))
async def cb_lang(cq: CallbackQuery, callback_data: V.Cb, state: FSMContext, db: Database,
                  user_name: str | None):
    lang = callback_data.k if callback_data.k in LANGUAGES else "en"
    await db.set_lang(cq.from_user.id, lang)
    await cq.answer(t(lang, "lang_set"))
    if not user_name:  # still registering: re-show the welcome in the new language
        await state.set_state(St.name)
        await safe_edit(cq, f"{t(lang, 'welcome')}\n\n{t(lang, 'choose_lang_hint')}", V.lang_kb())
        return
    await safe_edit(cq, t(lang, "lang_set"))
    await cq.message.answer(t(lang, "use_menu"), reply_markup=V.main_menu(lang))


@router.message(btn("btn_name"))
@router.message(Command("name"))
async def ask_name(msg: Message, state: FSMContext, lang: str, user_name: str | None):
    await state.set_state(St.name)
    await msg.answer(t(lang, "name_current", name=escape(user_name or "—")),
                     reply_markup=V.input_menu(lang, []))


@router.message(btn("btn_cancel"))
@router.message(Command("cancel"))
async def cancel(msg: Message, state: FSMContext, lang: str, user_name: str | None):
    if not user_name:
        await state.set_state(St.name)
        await msg.answer(t(lang, "name_first"))
        return
    await back_to_menu(msg, state, lang, t(lang, "cancelled"))


@router.message(St.name, Filter.text)
async def save_name(msg: Message, state: FSMContext, db: Database, lang: str):
    name = msg.text.strip()
    if not 2 <= len(name) <= 40:
        await msg.answer(t(lang, "name_len"))
        return
    await db.set_user_name(msg.from_user.id, name)
    await back_to_menu(msg, state, lang, t(lang, "name_saved", name=escape(name)))


# --- new flight wizard ----------------------------------------------------------------
async def ask_wizard_step(msg: Message, state: FSMContext, db: Database, lang: str):
    step = (await state.get_data())["step"]
    key = F.WIZARD[step]
    recent = await db.recent_values(msg.from_user.id, key)
    await msg.answer(
        f"{t(lang, 'step', n=step + 1, total=len(F.WIZARD))}\n{V.prompt_for(lang, key)}",
        reply_markup=V.input_menu(lang, suggestions_for(lang, key, recent), skip=key not in F.REQUIRED),
    )


@router.message(btn("btn_new"))
@router.message(Command("new"))
async def new_flight(msg: Message, state: FSMContext, db: Database, lang: str, user_name: str | None):
    if not await require_name(msg, state, lang, user_name):
        return
    await state.set_state(St.wizard)
    await state.set_data({"step": 0, "values": {}})
    await ask_wizard_step(msg, state, db, lang)


@router.message(St.wizard, Filter.text)
async def wizard_input(msg: Message, state: FSMContext, db: Database, lang: str):
    data = await state.get_data()
    step, values = data["step"], data["values"]
    key = F.WIZARD[step]
    kind = F.HEADER[key][2]
    if not (msg.text in all_variants("btn_skip") and key not in F.REQUIRED):
        try:
            values[key] = parse_input(kind, msg.text)
        except ValueError:
            await msg.answer(t(lang, "invalid", hint=hint(lang, kind, key)))
            return
    step += 1
    if step < len(F.WIZARD):
        await state.update_data(step=step, values=values)
        await ask_wizard_step(msg, state, db, lang)
        return
    fid = await db.create_flight(msg.from_user.id, values)
    await back_to_menu(msg, state, lang, t(lang, "flight_created"))
    await send_card(msg, db, lang, fid, msg.from_user.id)


# --- flight list & card ---------------------------------------------------------------
@router.message(btn("btn_list"))
@router.message(Command("flights"))
async def my_flights(msg: Message, state: FSMContext, db: Database, lang: str, user_name: str | None):
    if not await require_name(msg, state, lang, user_name):
        return
    await state.clear()
    flights = await db.list_flights(msg.from_user.id)
    if not flights:
        await msg.answer(t(lang, "no_flights"), reply_markup=V.main_menu(lang))
        return
    await msg.answer(t(lang, "your_flights"), reply_markup=V.flights_kb(flights))


@router.callback_query(V.Cb.filter(Filter.a == "list"))
async def cb_list(cq: CallbackQuery, db: Database, lang: str):
    flights = await db.list_flights(cq.from_user.id)
    await safe_edit(cq, t(lang, "your_flights") if flights else t(lang, "no_flights"), V.flights_kb(flights))
    await cq.answer()


# Any other flight callback: load the flight first, ownership is enforced here.
@router.callback_query(V.Cb.filter())
async def cb_flight(cq: CallbackQuery, callback_data: V.Cb, state: FSMContext, db: Database, lang: str,
                    user_name: str | None):
    a, fid, key, which = callback_data.a, callback_data.id, callback_data.k, callback_data.w
    uid = cq.from_user.id
    flight, checks, times = await load(db, fid, uid)
    if not flight:
        await cq.answer(t(lang, "not_found"), show_alert=True)
        return
    toast = None

    if a == "card":
        await state.clear()
        await safe_edit(cq, V.card_text(lang, flight, checks, times), V.card_kb(lang, fid))

    elif a == "hdr":
        await safe_edit(cq, t(lang, "header_title"), V.header_kb(lang, flight))

    elif a == "hset" and key in F.HEADER:
        await state.set_state(St.field)
        await state.set_data({"fid": fid, "key": key})
        recent = await db.recent_values(uid, key)
        await cq.message.answer(
            f"{t(lang, 'current', value=escape(flight.get(key) or '—'))}\n{V.prompt_for(lang, key)}",
            reply_markup=V.input_menu(lang, suggestions_for(lang, key, recent), clear=key not in F.REQUIRED,
                                      nil=key in F.NIL_FIELDS, dash=key in F.DASH_FIELDS),
        )

    elif a == "docs":
        await safe_edit(cq, t(lang, "docs_text"), V.docs_kb(lang, fid, checks))

    elif a == "chk" and key in dict(F.CHECKLIST):
        new = F.CHECK_CYCLE[checks.get(key)]
        await db.set_check(fid, key, new)
        checks[key] = new
        if new is None:
            checks.pop(key)
        await safe_edit(cq, t(lang, "docs_text"), V.docs_kb(lang, fid, checks))

    elif a == "chkdef":
        await db.set_checks(fid, F.CHECKLIST_DEFAULT)
        await safe_edit(cq, t(lang, "docs_text"), V.docs_kb(lang, fid, {**checks, **F.CHECKLIST_DEFAULT}))
        toast = t(lang, "default_applied")

    elif a == "tl":
        await state.clear()
        await safe_edit(cq, t(lang, "timeline_text"), V.timeline_kb(lang, fid, times))

    elif a == "ev" and key in F.EVENT_BY_KEY:
        await safe_edit(cq, V.event_text(lang, key, times), V.event_kb(lang, fid, key))

    elif a == "now" and key in F.EVENT_BY_KEY and which in (1, 2):
        now = F.now_tashkent().strftime("%H%M")
        await db.set_time(fid, key, which, now)
        times = await db.get_times(fid)
        await safe_edit(cq, t(lang, "timeline_text"), V.timeline_kb(lang, fid, times))
        toast = f"{label(lang, key)}: {now}"

    elif a == "tset" and key in F.EVENT_BY_KEY and which in (1, 2):
        await state.set_state(St.time)
        await state.set_data({"fid": fid, "key": key, "which": which})
        _, pair = F.EVENT_BY_KEY[key]
        name = label(lang, key) + (f" — {part(lang, pair[which - 1])}" if pair else "")
        await cq.message.answer(t(lang, "time_prompt", label=name), reply_markup=V.input_menu(lang, []))

    elif a == "tdash" and key in F.EVENT_BY_KEY:
        await db.clear_time(fid, key)
        await db.set_time(fid, key, 1, F.DASH)
        times = await db.get_times(fid)
        await safe_edit(cq, t(lang, "timeline_text"), V.timeline_kb(lang, fid, times))
        toast = f"{label(lang, key)}: {F.DASH_PRINT}"

    elif a == "tclr" and key in F.EVENT_BY_KEY:
        await db.clear_time(fid, key)
        times.pop(key, None)
        await safe_edit(cq, t(lang, "timeline_text"), V.timeline_kb(lang, fid, times))
        toast = t(lang, "cleared")

    elif a == "rem":
        await safe_edit(cq, V.remarks_text(lang, flight.get("remarks")),
                        V.remarks_kb(lang, fid, bool(flight.get("remarks"))))

    elif a == "remset":
        await state.set_state(St.remarks)
        await state.set_data({"fid": fid})
        await cq.message.answer(t(lang, "remarks_prompt", max=F.REMARKS_MAX), reply_markup=V.input_menu(lang, []))

    elif a == "remclr":
        await db.set_field(fid, uid, "remarks", None)
        await safe_edit(cq, V.remarks_text(lang, None), V.remarks_kb(lang, fid, False))

    elif a == "pdf":
        await cq.answer(t(lang, "generating"))
        data = await asyncio.to_thread(build_pdf, flight, checks, times, user_name or "")
        filename = (f"{(flight.get('flight') or 'flight').replace('/', '-')}_"
                    f"{(flight.get('date') or '').replace('.', '')}.pdf")
        await cq.message.answer_document(
            BufferedInputFile(data, filename),
            caption=f"✈️ {escape(flight.get('flight') or '')} · {escape(flight.get('date') or '')}",
        )
        return

    elif a == "del":
        await safe_edit(cq, t(lang, "delete_q", flight=escape(flight.get("flight") or "")),
                        V.confirm_delete_kb(lang, fid))

    elif a == "delok":
        await db.delete_flight(fid, uid)
        flights = await db.list_flights(uid)
        text = t(lang, "deleted") + ("\n" + t(lang, "your_flights") if flights else "")
        await safe_edit(cq, text, V.flights_kb(flights))

    await cq.answer(toast)


# --- text inputs started from inline buttons ------------------------------------------
async def _fid_or_reset(msg: Message, state: FSMContext, db: Database, lang: str):
    data = await state.get_data()
    flight = await db.get_flight(data.get("fid", 0), msg.from_user.id)
    if not flight:
        await back_to_menu(msg, state, lang, t(lang, "not_found"))
        return None, data
    return flight["id"], data


@router.message(St.field, Filter.text)
async def field_input(msg: Message, state: FSMContext, db: Database, lang: str):
    fid, data = await _fid_or_reset(msg, state, db, lang)
    if not fid:
        return
    key = data["key"]
    kind = F.HEADER[key][2]
    text = msg.text.strip()
    if text in all_variants("btn_clear") and key not in F.REQUIRED:
        value = None
    elif key in F.NIL_FIELDS and (text in all_variants("btn_nil") or text.upper() == F.NIL):
        value = F.NIL
    elif key in F.DASH_FIELDS and (text in all_variants("btn_dash") or set(text) <= {"-", "—", "–"}):
        value = F.DASH
    else:
        try:
            value = parse_input(kind, text)
        except ValueError:
            await msg.answer(t(lang, "invalid", hint=hint(lang, kind, key)))
            return
        if key in F.INFANT_FIELDS and "+" not in value:
            await state.set_state(St.infants)
            await state.update_data(pax=value)
            await msg.answer(t(lang, "infants_q", label=label(lang, key), pax=value),
                             reply_markup=V.infants_menu(lang))
            return
    await save_field(msg, state, db, lang, fid, key, value)


async def save_field(msg: Message, state: FSMContext, db: Database, lang: str, fid: int, key: str,
                     value: str | None):
    await db.set_field(fid, msg.from_user.id, key, value)
    shown = F.DASH_PRINT if value == F.DASH else (value or "—")
    await back_to_menu(msg, state, lang, t(lang, "field_saved", label=label(lang, key), value=escape(shown)))
    flight = await db.get_flight(fid, msg.from_user.id)
    await msg.answer(t(lang, "header_title"), reply_markup=V.header_kb(lang, flight))


@router.message(St.infants, Filter.text)
async def infants_input(msg: Message, state: FSMContext, db: Database, lang: str):
    fid, data = await _fid_or_reset(msg, state, db, lang)
    if not fid:
        return
    text = msg.text.strip()
    if text in all_variants("btn_no_infants"):
        infants = 0
    elif text.isdigit() and len(text) <= 3:
        infants = int(text)
    else:
        await msg.answer(t(lang, "invalid", hint=t(lang, "hint_infants")))
        return
    await save_field(msg, state, db, lang, fid, data["key"], F.with_infants(data["pax"], infants))


@router.message(St.time, Filter.text)
async def time_input(msg: Message, state: FSMContext, db: Database, lang: str):
    fid, data = await _fid_or_reset(msg, state, db, lang)
    if not fid:
        return
    try:
        value = F.parse_time(msg.text)
    except ValueError:
        await msg.answer(t(lang, "invalid_time", hint=hint(lang, "time")))
        return
    await db.set_time(fid, data["key"], data["which"], value)
    await back_to_menu(msg, state, lang, t(lang, "time_saved", value=value))
    await msg.answer(t(lang, "timeline_text"), reply_markup=V.timeline_kb(lang, fid, await db.get_times(fid)))


@router.message(St.remarks, Filter.text)
async def remarks_input(msg: Message, state: FSMContext, db: Database, lang: str):
    fid, _ = await _fid_or_reset(msg, state, db, lang)
    if not fid:
        return
    text = msg.text.strip()
    if len(text) > F.REMARKS_MAX:
        await msg.answer(t(lang, "remarks_long", n=len(text), max=F.REMARKS_MAX))
        return
    await db.set_field(fid, msg.from_user.id, "remarks", text)
    await back_to_menu(msg, state, lang, t(lang, "remarks_saved"))
    await send_card(msg, db, lang, fid, msg.from_user.id)


@router.message()
async def fallback(msg: Message, state: FSMContext, lang: str, user_name: str | None):
    if await require_name(msg, state, lang, user_name):
        await msg.answer(t(lang, "use_menu"), reply_markup=V.main_menu(lang))
