"""Form definition: every field on the cover sheet and the template cell it goes to.

If you move things around in template/cover_sheet.xlsx, update the cell addresses here.
"""
import re
from datetime import datetime, timedelta, timezone

# Uzbekistan has no daylight saving time, so a fixed offset is exact.
TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")


def now_tashkent() -> datetime:
    return datetime.now(TASHKENT)


def date_suggestions() -> tuple[str, str]:
    """Today and tomorrow in Tashkent, formatted like the form (dd.mm.yy)."""
    today = now_tashkent()
    return today.strftime("%d.%m.%y"), (today + timedelta(days=1)).strftime("%d.%m.%y")


# --- Header ------------------------------------------------------------------
# key: (label, template cell, value kind)
HEADER = {
    "date":    ("DATE",              "B5",  "date"),
    "from_st": ("FROM",              "D5",  "station"),
    "to_st":   ("TO",                "I5",  "station"),
    "flight":  ("FLIGHT NUMBER",     "B6",  "flight"),
    "ac":      ("TYPE/REGISTRATION", "I6",  "text"),
    "sta":     ("STA",               "B7",  "time"),
    "park":    ("PARK POSITION",     "I7",  "text"),
    "std":     ("STD",               "B8",  "time"),
    "delay":   ("DELAY",             "I8",  "text"),
    "pax_in":  ("PAX IN",            "B9",  "int"),
    "pax_out": ("PAX OUT",           "D9",  "int"),
    "trs":     ("TRS.PX",            "I9",  "int"),
    "cgo_in":  ("CGO IN",            "B10", "text"),
    "cgo_out": ("CGO OUT",           "D10", "text"),
    "bag_in":  ("BAG IN",            "B11", "text"),
    "bag_out": ("BAG OUT",           "D11", "text"),
}

# Asked one after another when a new flight is created; the rest is edited later.
WIZARD = ["date", "flight", "from_st", "to_st", "ac", "sta", "std", "park"]
REQUIRED = {"flight"}

# --- Documents checklist ------------------------------------------------------
# (key, short button label); rows 15..31, ticks go to columns E/F/G.
CHECKLIST = [
    ("cover", "Cover sheet"),
    ("service", "Service form"),
    ("loadsheet", "Loadsheet"),
    ("tripinfo", "Trip info"),
    ("lir", "LIR (signed)"),
    ("paxman", "Pax manifest"),
    ("bagman", "Bag manifest"),
    ("bingo", "Bingo sheet"),
    ("fuel", "Fuel order"),
    ("workorder", "Work order"),
    ("messages", "Messages"),
    ("techlog", "Tech logbook"),
    ("incident", "Incident docs"),
    ("deicing", "De-icing order"),
    ("cargoman", "Cargo manifest"),
    ("journeylog", "Journey log"),
    ("dgr", "DGR / NOTOC"),
]
CHECKLIST_FIRST_ROW = 15
CHECK_COLUMNS = {"Y": "E", "N": "F", "NA": "G"}
CHECK_MARK = "✓"
CHECK_ICONS = {"Y": "✅", "N": "❌", "NA": "➖", None: "▫️"}
CHECK_CYCLE = {None: "Y", "Y": "N", "N": "NA", "NA": None}

# "Apply default" button; same pattern as the sample sheet. Edit freely.
CHECKLIST_DEFAULT = {k: "Y" for k, _ in CHECKLIST[:11]}
CHECKLIST_DEFAULT["tripinfo"] = "N"
CHECKLIST_DEFAULT.update({k: "NA" for k, _ in CHECKLIST[11:]})

# --- Turnaround timeline ------------------------------------------------------
# (key, short label, (first, second) labels if start/finish pair else None);
# rows 14..32, times go to column J.
EVENTS = [
    ("equipment", "All equipment", None),
    ("ata", "ATA / On block", ("ATA", "On block")),
    ("stairs", "Air stairs / PBB", None),
    ("door_open", "Door opened", None),
    ("deboard", "Deboarding", ("Start", "Finish")),
    ("unload", "Unloading bags", ("Start", "Finish")),
    ("avsec", "AvSec check", ("Start", "Finish")),
    ("cleaning", "Cleaning", ("Start", "Finish")),
    ("catering", "Catering", ("Start", "Finish")),
    ("fueling", "Fueling", ("Start", "Finish")),
    ("toilet", "Toilet service", ("Start", "Finish")),
    ("water", "Water service", ("Start", "Finish")),
    ("ready", "Ready to board", None),
    ("boarding", "Boarding", ("Start", "Finish")),
    ("loading", "Loading bags", ("Start", "Finish")),
    ("door_closed", "Door closed", None),
    ("offblock", "Off block", None),
    ("pushback", "Pushback", None),
    ("takeoff", "Take off", None),
]
EVENTS_FIRST_ROW = 14
EVENT_COLUMN = "J"
EVENT_BY_KEY = {k: (label, pair) for k, label, pair in EVENTS}

# --- Remarks & signature ------------------------------------------------------
# Remarks are wrapped over these line cells (merged ranges in the template).
REMARK_LINES = ["C34", "A35", "A36", "A37", "A38"]
REMARKS_MAX = 450
SIGNATURE_CELL = "I41"


# --- Validation ---------------------------------------------------------------
def parse_value(kind: str, text: str) -> str:
    """Normalise user input or raise ValueError(kind); the bot shows the hint for that kind."""
    t = text.strip()
    if kind == "date":
        m = re.fullmatch(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2}|\d{4})", t)
        if not m:
            raise ValueError("date")
        d, mth, y = int(m[1]), int(m[2]), int(m[3]) % 100
        try:
            datetime(2000 + y, mth, d)
        except ValueError:
            raise ValueError("date") from None
        return f"{d:02d}.{mth:02d}.{y:02d}"
    if kind == "time":
        return parse_time(t)
    if kind == "station":
        if not re.fullmatch(r"[A-Za-z]{3,4}", t):
            raise ValueError("station")
        return t.upper()
    if kind == "flight":
        if not re.fullmatch(r"[A-Za-z0-9]{2,3}\s?\d{1,4}[A-Za-z]?(\s?/\s?\d{1,4}[A-Za-z]?)?", t):
            raise ValueError("flight")
        return re.sub(r"\s", "", t).upper()
    if kind == "int":
        if not re.fullmatch(r"\d{1,4}", t):
            raise ValueError("int")
        return str(int(t))
    if not t or len(t) > 40:
        raise ValueError("text")
    return t


def parse_time(t: str) -> str:
    m = re.fullmatch(r"(\d{1,2})[:.]?(\d{2})", t.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        raise ValueError("time")
    return f"{int(m[1]):02d}{m[2]}"


def format_event(t1: str | None, t2: str | None) -> str:
    """How a timeline value is written on the sheet: 0750/0759, 0800 or /0820."""
    if t1 and t2:
        return f"{t1}/{t2}"
    if t2:
        return f"/{t2}"
    return t1 or ""
