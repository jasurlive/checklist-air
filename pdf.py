"""Fill the Excel template with a flight and draw it to PDF.

The layout (column widths, row heights, merges, borders, fonts, logo, page setup)
is read from template/cover_sheet.xlsx, so the PDF follows whatever the template
looks like. Pure Python: openpyxl + reportlab, no LibreOffice needed.
"""
import io
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter, range_boundaries
from openpyxl.utils.cell import coordinate_from_string
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import fields as F

BASE = Path(__file__).parent
TEMPLATE = BASE / "template" / "cover_sheet.xlsx"
EMU_PER_PT = 12700

# Text styles. The title keeps the template's own font, in black.
# Printed labels (everything else in the template) are bold, in the blue of the logo.
# Values filled in from the bot are a bit larger, in ballpoint-pen blue, so they read as handwriting.
TITLE_CELLS = {"C1"}
TITLE_SIZE = 15.0
TITLE_COLOR = (0, 0, 0)
LABEL_COLOR = (0x00 / 255, 0x6F / 255, 0xB9 / 255)  # #006FB9, sampled from the logo
LABEL_SIZE = 12.0
VALUE_COLOR = (0x1A / 255, 0x2E / 255, 0x9E / 255)  # #1A2E9E, pen blue
VALUE_SIZE = 15.0
# A value too long for its cell is shrunk, but never below this.
MIN_FONT = 7.0

# Excel font name -> (regular, bold) TTF. Carlito is metric-compatible with Calibri.
_FONT_FILES = {
    "Calibri": ("Carlito-Regular.ttf", "Carlito-Bold.ttf"),
    "DejaVu Sans": ("DejaVuSans.ttf", "DejaVuSans.ttf"),
}
for _name, (_reg, _bold) in _FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(f"{_name}", str(BASE / "fonts" / _reg)))
    pdfmetrics.registerFont(TTFont(f"{_name}-Bold", str(BASE / "fonts" / _bold)))


def _font(cell_font) -> tuple[str, float]:
    name = cell_font.name if cell_font.name in _FONT_FILES else "Calibri"
    return (f"{name}-Bold" if cell_font.b else name), float(cell_font.sz or 11)


# --- Filling ------------------------------------------------------------------
def fill_template(flight: dict, checks: dict, times: dict, signature: str):
    """Return an openpyxl worksheet with the flight's data written in."""
    ws = load_workbook(TEMPLATE).active
    before = {c.coordinate for row in ws.iter_rows() for c in row if c.value not in (None, "")}
    for key, (_, cell, _) in F.HEADER.items():
        if flight.get(key):
            ws[cell] = F.DASH_PRINT if flight[key] == F.DASH else flight[key]
    for i, (key, _) in enumerate(F.CHECKLIST):
        col = F.CHECK_COLUMNS.get(checks.get(key))
        if col:
            ws[f"{col}{F.CHECKLIST_FIRST_ROW + i}"] = F.CHECK_MARK
    for i, (key, _, _) in enumerate(F.EVENTS):
        t1, t2 = times.get(key, (None, None))
        ws[f"{F.EVENT_COLUMN}{F.EVENTS_FIRST_ROW + i}"] = F.format_event(t1, t2) or None
    if flight.get("remarks"):
        _fill_remarks(ws, flight["remarks"])
    ws[F.SIGNATURE_CELL] = signature
    # Name on the left, leaving room on the right for a handwritten signature.
    sig = ws[F.SIGNATURE_CELL]
    sig.alignment = sig.alignment.copy(horizontal="left")
    # Everything that was not printed on the template is a filled-in value.
    ws.filled_cells = {c.coordinate for row in ws.iter_rows() for c in row
                       if c.value not in (None, "")} - before
    return ws


def _fill_remarks(ws, text: str):
    # Wrap at the value size; if the text is too long for the lines, wrap smaller (drawn smaller too).
    for size in (VALUE_SIZE, LABEL_SIZE):
        lines = _wrap_remarks(ws, text, size)
        if len(lines) <= len(F.REMARK_LINES):
            break
    cells = F.REMARK_LINES
    if len(lines) > len(cells):
        lines = lines[: len(cells)]
        lines[-1] = lines[-1][:-1] + "…"
    for cell, line in zip(cells, lines):
        ws[cell] = line or None


def _wrap_remarks(ws, text: str, size: float) -> list[str]:
    geo = _Geometry(ws)
    lines: list[str] = []
    cells = F.REMARK_LINES
    for para in text.splitlines() or [""]:
        current = ""
        for word in para.split():
            cell = cells[min(len(lines), len(cells) - 1)]
            font = _font(ws[cell].font)[0].removesuffix("-Bold")
            trial = f"{current} {word}".strip()
            if pdfmetrics.stringWidth(trial, font, size) <= geo.cell_width(cell) - 6:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


# --- Rendering ----------------------------------------------------------------
class _Geometry:
    """Cell positions in points, relative to the print area's top-left corner."""

    def __init__(self, ws):
        self.ws = ws
        area = ws.print_area
        if area:
            area = area.split("!")[-1].replace("$", "")
            c1, r1, c2, r2 = range_boundaries(area)
        else:
            c1, r1, c2, r2 = 1, 1, ws.max_column, ws.max_row
        self.c1, self.r1, self.c2, self.r2 = c1, r1, c2, r2
        self.x = {c1: 0.0}
        for c in range(c1, c2 + 1):
            dim = ws.column_dimensions.get(get_column_letter(c))
            width = dim.width if dim is not None and dim.width else 8.43
            self.x[c + 1] = self.x[c] + (width * 7 + 5) * 0.75  # chars -> px -> pt
        self.y = {r1: 0.0}
        default_h = ws.sheet_format.defaultRowHeight or 15
        for r in range(r1, r2 + 1):
            dim = ws.row_dimensions.get(r)
            height = dim.height if dim is not None and dim.height else default_h
            self.y[r + 1] = self.y[r] + height
        self.width = self.x[c2 + 1]
        self.height = self.y[r2 + 1]
        self.merged = {}
        self.hidden = set()
        self.owner = {}  # cell -> (min_row, min_col, max_row, max_col) of its merge
        for rng in ws.merged_cells.ranges:
            bounds = (rng.min_row, rng.min_col, rng.max_row, rng.max_col)
            self.merged[(rng.min_row, rng.min_col)] = (rng.max_row, rng.max_col)
            for r in range(rng.min_row, rng.max_row + 1):
                for c in range(rng.min_col, rng.max_col + 1):
                    self.owner[(r, c)] = bounds
                    if (r, c) != (rng.min_row, rng.min_col):
                        self.hidden.add((r, c))

    def span(self, r, c):
        r2, c2 = self.merged.get((r, c), (r, c))
        return self.x[c], self.y[r], self.x[c2 + 1], self.y[r2 + 1]

    def cell_width(self, coord):
        col, row = coordinate_from_string(coord)
        c = column_index_from_string(col)
        x1, _, x2, _ = self.span(row, c)
        return x2 - x1


_LINE = {"thin": (0.6, None), "medium": (1.2, None), "thick": (2.0, None),
         "hair": (0.3, None), "dotted": (0.6, [0.8, 2]), "dashed": (0.6, [3, 2])}


def _wrap(text, font, size, width):
    lines = []
    for para in str(text).split("\n"):
        current = ""
        for word in para.split(" "):
            trial = f"{current} {word}" if current else word
            if pdfmetrics.stringWidth(trial, font, size) <= width or not current:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def render_pdf(ws) -> bytes:
    g = _Geometry(ws)
    page_w, page_h = A4
    m = ws.page_margins
    left, right, top, bottom = (m.left * 72, m.right * 72, m.top * 72, m.bottom * 72)
    avail_w, avail_h = page_w - left - right, page_h - top - bottom
    scale = min(1.0, avail_w / g.width, avail_h / g.height)
    if ws.print_options.horizontalCentered:
        left += (avail_w - g.width * scale) / 2

    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=A4)
    pdf.setTitle("Station Trip File Cover Sheet")
    # Excel coordinates: origin top-left, y down. Flip once here.
    pdf.translate(left, page_h - top)
    pdf.scale(scale, -scale)

    for r in range(g.r1, g.r2 + 1):
        for c in range(g.c1, g.c2 + 1):
            cell = ws.cell(r, c)
            _draw_borders(pdf, g, cell, r, c)
            if (r, c) not in g.hidden and cell.value not in (None, ""):
                _draw_text(pdf, g, cell, r, c)

    for img in ws._images:
        _draw_image(pdf, g, img)

    pdf.showPage()
    pdf.save()
    return buf.getvalue()


def _draw_borders(pdf, g, cell, r, c):
    x1, y1, x2, y2 = g.x[c], g.y[r], g.x[c + 1], g.y[r + 1]
    b = cell.border
    mr1, mc1, mr2, mc2 = g.owner.get((r, c), (r, c, r, c))
    inner = {"left": c > mc1, "right": c < mc2, "top": r > mr1, "bottom": r < mr2}
    for side, coords in (("left", (x1, y1, x1, y2)), ("right", (x2, y1, x2, y2)),
                         ("top", (x1, y1, x2, y1)), ("bottom", (x1, y2, x2, y2))):
        style = getattr(getattr(b, side), "style", None)
        if not style or inner[side]:
            continue
        width, dash = _LINE.get(style, _LINE["thin"])
        pdf.setLineWidth(width)
        pdf.setDash(dash or [])
        pdf.line(*coords)
    pdf.setDash([])


def _fit(text, font, size, width, height, wrap):
    """Keep the size if the text fits on one line, or wrapped (labels only); else shrink.

    Returns (size, lines, line spacing factor).
    """
    while True:
        if pdfmetrics.stringWidth(text, font, size) <= width and "\n" not in text:
            return size, [text], 1.15
        if wrap:
            lines = _wrap(text, font, size, width)
            widest = max(pdfmetrics.stringWidth(line, font, size) for line in lines)
            if widest <= width and size * len(lines) <= height:
                return size, lines, (1.15 if size * 1.15 * len(lines) <= height else 1.0)
        if size <= MIN_FONT:
            return size, [text], 1.15
        size = max(MIN_FONT, size - 0.25)


def _style(ws, cell) -> tuple[str, float, tuple]:
    """(font, size, colour) for a cell: title, filled-in value or printed label."""
    font, size = _font(cell.font)
    family = font.removesuffix("-Bold")
    if cell.coordinate in TITLE_CELLS:
        return font, TITLE_SIZE, TITLE_COLOR
    if cell.coordinate in getattr(ws, "filled_cells", ()):
        return family, VALUE_SIZE, VALUE_COLOR
    return f"{family}-Bold", LABEL_SIZE, LABEL_COLOR


def _draw_text(pdf, g, cell, r, c):
    x1, y1, x2, y2 = g.span(r, c)
    font, size, color = _style(g.ws, cell)
    al = cell.alignment
    pad = 3
    text = str(cell.value)
    pdf.setFillColorRGB(*color)
    pdf.setStrokeColorRGB(*color)

    if text == F.DASH_PRINT:  # "not applicable": a long dash across the middle of the cell
        y, half = (y1 + y2) / 2, min((x2 - x1) * 0.3, 30)
        if al.horizontal == "center":
            mid = (x1 + x2) / 2
        else:
            mid = x1 + pad + half
        pdf.setLineWidth(1.2)
        pdf.line(mid - half, y, mid + half, y)
        pdf.setStrokeColorRGB(0, 0, 0)
        return

    is_label = color == LABEL_COLOR
    size, lines, spacing = _fit(text, font, size, x2 - x1 - 2 * pad, y2 - y1 - 2, al.wrap_text or is_label)
    line_h = size * spacing
    block_h = line_h * len(lines)
    if al.vertical == "top":
        base = y1 + pad + size * 0.8
    elif al.vertical == "center":
        base = (y1 + y2) / 2 - block_h / 2 + size * 0.8
    else:  # Excel default: bottom
        base = y2 - pad - block_h + size * 0.8

    for i, line in enumerate(lines):
        y = base + i * line_h
        w = pdfmetrics.stringWidth(line, font, size)
        if al.horizontal == "center":
            x = (x1 + x2 - w) / 2
        elif al.horizontal == "right":
            x = x2 - pad - w
        else:
            x = x1 + pad
        # Text must be drawn un-flipped.
        pdf.saveState()
        pdf.translate(x, y)
        pdf.scale(1, -1)
        pdf.setFont(font, size)
        pdf.drawString(0, 0, line)
        pdf.restoreState()
    pdf.setStrokeColorRGB(0, 0, 0)


def _draw_image(pdf, g, img):
    anchor = img.anchor
    if isinstance(anchor, str):
        col, row = coordinate_from_string(anchor)
        c, r, dx, dy = column_index_from_string(col), row, 0, 0
    else:
        c, r = anchor._from.col + 1, anchor._from.row + 1
        dx, dy = anchor._from.colOff / EMU_PER_PT, anchor._from.rowOff / EMU_PER_PT
    x, y = g.x.get(c, 0) + dx, g.y.get(r, 0) + dy
    ext = getattr(anchor, "ext", None)
    if ext is not None and getattr(ext, "width", None):
        w, h = ext.width / EMU_PER_PT, ext.height / EMU_PER_PT
    elif hasattr(anchor, "to") and anchor.to is not None:
        x2 = g.x.get(anchor.to.col + 1, g.width) + anchor.to.colOff / EMU_PER_PT
        y2 = g.y.get(anchor.to.row + 1, g.height) + anchor.to.rowOff / EMU_PER_PT
        w, h = x2 - x, y2 - y
    else:
        w, h = img.width * 0.75, img.height * 0.75
    reader = ImageReader(io.BytesIO(img._data()))
    pdf.saveState()
    pdf.translate(x, y + h)
    pdf.scale(1, -1)
    pdf.drawImage(reader, 0, 0, w, h, mask="auto")
    pdf.restoreState()


def build_pdf(flight: dict, checks: dict, times: dict, signature: str) -> bytes:
    return render_pdf(fill_template(flight, checks, times, signature))
