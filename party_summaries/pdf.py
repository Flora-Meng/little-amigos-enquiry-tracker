from io import BytesIO
import re

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:  # Lightweight local fallback until dependencies are installed.
    colors = None
    A4 = (595.2756, 841.8898)
    ImageReader = None
    stringWidth = None
    canvas = None
    REPORTLAB_AVAILABLE = False

from .models import PartyMenuItem


if REPORTLAB_AVAILABLE:
    PEACH = colors.HexColor("#F68F6F")
    INK = colors.HexColor("#21313A")
    MUTED = colors.HexColor("#68777F")
    BORDER = colors.HexColor("#DED9CF")
    PALE = colors.HexColor("#FCFAF5")
    AQUA = colors.HexColor("#E7F7F3")
else:
    PEACH = INK = MUTED = BORDER = PALE = AQUA = None


def _safe(value):
    return str(value or "").replace("\u2013", "-").replace("\u2014", "-").replace("\u2011", "-")


def _fit(text, width, font="Helvetica", size=8):
    text = _safe(text)
    if stringWidth(text, font, size) <= width:
        return text
    while text and stringWidth(text + "...", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "..."


def _wrap_lines(text, width, font="Helvetica", size=8):
    paragraphs = _safe(text).splitlines() or [""]
    lines = []
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if not line or stringWidth(candidate, font, size) <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines or [""]


def _numeric_quantity(value):
    match = re.match(r"\s*(\d+(?:\.\d+)?)", _safe(value))
    return match.group(1) if match else _safe(value)


def _pdf_escape(value):
    return _safe(value).encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _jpeg_dimensions(data):
    if not data.startswith(b"\xff\xd8"):
        return None
    index = 2
    while index + 9 < len(data):
        if data[index] != 0xFF:
            index += 1
            continue
        marker = data[index + 1]
        index += 2
        if marker in {0xD8, 0xD9}:
            continue
        if index + 2 > len(data):
            return None
        length = int.from_bytes(data[index:index + 2], "big")
        if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
            if index + 7 > len(data):
                return None
            return int.from_bytes(data[index + 5:index + 7], "big"), int.from_bytes(data[index + 3:index + 5], "big")
        index += max(length, 2)
    return None


def _build_fallback_pdf(summary):
    menu_items = list(summary.menu_items.all())
    bill_items = list(summary.bill_items.all())
    sections = [
        ("PARTY DETAILS", [
            f"Date: {summary.party_date:%d %B %Y}    Party time: {summary.party_time}    Food ready: {summary.food_ready}",
            f"Owner: {summary.owner_name}    Phone: {summary.owner_number}",
            f"Location: {summary.location.name}    Room: {summary.get_room_type_display()}",
            f"Guests: {summary.kids_count} kids / {summary.adults_count} adults    Deposit method: {summary.deposit_method}",
        ]),
        ("ADULT MENU", [f"{item.quantity}  {item.item}{f' - {item.notes}' if item.notes else ''}" for item in menu_items if item.category == PartyMenuItem.Category.ADULT]),
        ("KIDS MENU - 1 DRINK PER CHILD", [
            *[f"{item.quantity}  {item.item}{f' - {item.notes}' if item.notes else ''}" for item in menu_items if item.category == PartyMenuItem.Category.KIDS],
            f"Dietary requirements: {summary.dietary_requirements or 'None advised'}",
        ]),
        ("EXTRA FOOD", [f"{item.quantity}  {item.item}{f' - {item.notes}' if item.notes else ''}  ${item.amount:,.2f}" for item in menu_items if item.category == PartyMenuItem.Category.EXTRA]),
        ("BIRTHDAY CHILD & SETUP", [
            f"Kids name: {summary.kids_name}    Gender: {summary.get_gender_display()}    Age: {summary.age}",
            f"Theme: {summary.theme}    Balloon color: {summary.balloon_color}",
            f"Special note: {summary.special_note}",
            f"Decoration example: {summary.decoration_example_name or 'None'}",
        ]),
        ("BILL", [
            f"Deposit paid: -${summary.deposit_amount:,.2f}    Package: {summary.get_package_name_display()} ${summary.package_amount:,.2f}",
            f"Extra food: ${summary.extra_food_total:,.2f}    Food voucher: -${summary.food_voucher_amount:,.2f}    Other charges: ${summary.other_charges:,.2f}",
            *[f"{item.name}: ${item.amount:,.2f}" for item in bill_items],
            f"TOTAL BALANCE: ${summary.total_balance:,.2f}",
        ]),
    ]
    line_count = sum(len(lines) + 2 for _, lines in sections)
    font_size = min(9, max(5, 720 / max(line_count, 1) - 2))
    line_height = font_size + 3
    commands = ["0.13 0.19 0.23 rg", "BT", "/F2 19 Tf", "24 805 Td", "(PARTY SUMMARY) Tj", "ET"]
    y = 779
    for title, lines in sections:
        commands.extend(["BT", f"/F2 {font_size + 1:.2f} Tf", f"24 {y:.2f} Td", f"({_pdf_escape(title)}) Tj", "ET"])
        y -= line_height
        for line in lines or ["-"]:
            max_chars = max(45, int(104 * 7 / font_size))
            shown = _safe(line)
            chunks = [shown[index:index + max_chars] for index in range(0, len(shown), max_chars)] or [""]
            for chunk in chunks:
                commands.extend(["BT", f"/F1 {font_size:.2f} Tf", f"32 {y:.2f} Td", f"({_pdf_escape(chunk)}) Tj", "ET"])
                y -= line_height
        y -= line_height * 0.45
    image_data = bytes(summary.decoration_example or b"")
    image_dimensions = _jpeg_dimensions(image_data)
    if image_dimensions and y > 52:
        original_width, original_height = image_dimensions
        scale = min(300 / original_width, max(30, y - 40) / original_height)
        draw_width = original_width * scale
        draw_height = original_height * scale
        commands.extend(["0.41 0.47 0.50 rg", "BT", "/F2 6.5 Tf", f"24 {y - 5:.2f} Td", "(DECORATION EXAMPLE) Tj", "ET"])
        commands.append(f"q {draw_width:.2f} 0 0 {draw_height:.2f} 24 {max(22, y - draw_height - 17):.2f} cm /Im1 Do Q")
    commands.extend(["BT", "/F1 6 Tf", "410 12 Td", "(Generated by Little Amigos Workspace) Tj", "ET"])
    stream = "\n".join(commands).encode("latin-1")
    page_resources = "/Resources << /Font << /F1 5 0 R /F2 6 0 R >>"
    if image_dimensions:
        page_resources += " /XObject << /Im1 7 0 R >>"
    page_resources += " >>"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.2756 841.8898] {page_resources} /Contents 4 0 R >>".encode(),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
    ]
    if image_dimensions:
        original_width, original_height = image_dimensions
        objects.append(
            f"<< /Type /XObject /Subtype /Image /Width {original_width} /Height {original_height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(image_data)} >>\nstream\n".encode()
            + image_data + b"\nendstream"
        )
    output = BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    output.seek(0)
    return output


def _label_value(pdf, x, y, label, value, width, font_size=9):
    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(MUTED)
    pdf.drawString(x, y, label.upper())
    pdf.setFont("Helvetica", font_size)
    pdf.setFillColor(INK)
    for index, line in enumerate(_wrap_lines(value, width, size=font_size)):
        pdf.drawString(x, y - 11 - index * (font_size + 2), line)


def _section_box(pdf, x, top, width, height, title):
    bottom = top - height
    pdf.setStrokeColor(BORDER)
    pdf.setFillColor(colors.white)
    pdf.roundRect(x, bottom, width, height, 8, fill=1, stroke=1)
    pdf.setFillColor(PALE)
    pdf.roundRect(x, top - 24, width, 24, 8, fill=1, stroke=0)
    pdf.rect(x, top - 24, width, 8, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x + 10, top - 16, title)
    return bottom


def _menu_column(pdf, x, top, width, height, title, items, show_amount=False):
    _section_box(pdf, x, top, width, height, title)
    qty_width = 48
    amount_width = 42 if show_amount else 0
    item_width = width - qty_width - amount_width - 18
    available_height = height - 34
    font_size = 10
    prepared = []
    for candidate_size in (10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5):
        candidate_rows = []
        for item in items[:20]:
            quantity_lines = _wrap_lines(_numeric_quantity(item.quantity), qty_width - 4, "Helvetica-Bold", candidate_size)
            item_text = f"{item.item}\nNotes: {item.notes}" if item.notes else item.item
            item_lines = _wrap_lines(item_text, item_width, size=candidate_size)
            line_count = max(len(quantity_lines), len(item_lines))
            candidate_rows.append((item, quantity_lines, item_lines, line_count * (candidate_size + 2)))
        prepared = candidate_rows
        font_size = candidate_size
        if sum(row[3] for row in candidate_rows) <= available_height:
            break
    y = top - 34
    for item, quantity_lines, item_lines, row_height in prepared:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        for index, line in enumerate(quantity_lines):
            pdf.drawString(x + 8, y - index * (font_size + 2), line)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        for index, line in enumerate(item_lines):
            pdf.drawString(x + qty_width + 5, y - index * (font_size + 2), line)
        if show_amount:
            pdf.drawRightString(x + width - 8, y, f"${item.amount:,.2f}")
        y -= row_height


def _kids_menu_column(pdf, x, top, width, height, items, dietary_requirements):
    _section_box(pdf, x, top, width, height, "Kids menu - 1 drink per child")
    dietary_height = 67
    menu_bottom = top - height + dietary_height
    available_height = max(48, top - 30 - menu_bottom)
    qty_width = 39
    item_width = width - qty_width - 22
    font_size = 10
    prepared = []
    for candidate_size in (10, 9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5):
        candidate_rows = []
        for item in items[:20]:
            quantity_lines = _wrap_lines(item.quantity, qty_width, "Helvetica-Bold", candidate_size)
            item_text = f"{item.item}\nNotes: {item.notes}" if item.notes else item.item
            item_lines = _wrap_lines(item_text, item_width, size=candidate_size)
            line_count = max(len(quantity_lines), len(item_lines))
            candidate_rows.append((quantity_lines, item_lines, line_count * (candidate_size + 2)))
        prepared = candidate_rows
        font_size = candidate_size
        if sum(row[2] for row in candidate_rows) <= available_height:
            break
    y = top - 37
    for quantity_lines, item_lines, row_height in prepared:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        for index, line in enumerate(quantity_lines):
            pdf.drawString(x + 10, y - index * (font_size + 2), line)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        for index, line in enumerate(item_lines):
            pdf.drawString(x + 49, y - index * (font_size + 2), line)
        y -= row_height
    divider_y = top - height + dietary_height
    pdf.setStrokeColor(BORDER)
    pdf.line(x + 10, divider_y, x + width - 10, divider_y)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x + 10, divider_y - 15, "DIETARY REQUIREMENTS")
    pdf.setFillColor(INK)
    dietary_size = 9
    dietary_lines = []
    for candidate_size in (9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5):
        dietary_lines = _wrap_lines(dietary_requirements or "None advised", width - 20, size=candidate_size)
        dietary_size = candidate_size
        if len(dietary_lines) * (candidate_size + 3) <= dietary_height - 31:
            break
    pdf.setFont("Helvetica", dietary_size)
    for index, line in enumerate(dietary_lines):
        pdf.drawString(x + 10, divider_y - 29 - index * (dietary_size + 3), line)


def _extra_food_column(pdf, x, top, width, height, items, summary):
    _section_box(pdf, x, top, width, height, "Extra food")
    image_data = bytes(summary.decoration_example or b"")
    image_label_height = 18 if image_data else 0
    image_area_height = min(205, max(0, height * .56)) if image_data else 0
    menu_area_height = height - 29 - image_area_height - image_label_height
    qty_width = 32
    amount_width = 44
    item_width = width - qty_width - amount_width - 22
    font_size = 9.5
    prepared = []
    for candidate_size in (9.5, 9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5, 4.5):
        candidate_rows = []
        for item in items[:20]:
            quantity_lines = _wrap_lines(item.quantity, qty_width, "Helvetica-Bold", candidate_size)
            item_text = f"{item.item}\nNotes: {item.notes}" if item.notes else item.item
            item_lines = _wrap_lines(item_text, item_width, size=candidate_size)
            line_count = max(len(quantity_lines), len(item_lines))
            candidate_rows.append((item, quantity_lines, item_lines, line_count * (candidate_size + 2)))
        prepared = candidate_rows
        font_size = candidate_size
        if sum(row[3] for row in candidate_rows) <= menu_area_height:
            break
    y = top - 37
    for item, quantity_lines, item_lines, row_height in prepared:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        for index, line in enumerate(quantity_lines):
            pdf.drawString(x + 10, y - index * (font_size + 2), line)
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        for index, line in enumerate(item_lines):
            pdf.drawString(x + 47, y - index * (font_size + 2), line)
        pdf.drawRightString(x + width - 10, y, f"${item.amount:,.2f}")
        y -= row_height
    if not image_data:
        return
    label_y = top - height + image_area_height + 7
    pdf.setStrokeColor(BORDER)
    pdf.line(x + 10, label_y + 10, x + width - 10, label_y + 10)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(x + 10, label_y, "DECORATION EXAMPLE")
    try:
        image = ImageReader(BytesIO(image_data))
        image_width, image_original_height = image.getSize()
        max_width = width - 20
        max_height = image_area_height - 14
        ratio = min(max_width / image_width, max_height / image_original_height)
        draw_width = image_width * ratio
        draw_height = image_original_height * ratio
        pdf.drawImage(
            image, x + 10, top - height + 10,
            width=draw_width, height=draw_height,
            preserveAspectRatio=True, mask="auto",
        )
    except Exception:
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", 7)
        pdf.drawString(x + 10, top - height + image_area_height - 12, "Decoration image could not be rendered.")


def _draw_wrapped(pdf, text, x, y, width, font_size=7):
    lines = _wrap_lines(text, width, size=font_size)
    for index, value in enumerate(lines):
        pdf.drawString(x, y - index * (font_size + 3), value)
    return len(lines)


def build_party_summary_pdf(summary):
    if not REPORTLAB_AVAILABLE:
        return _build_fallback_pdf(summary)
    output = BytesIO()
    width, height = A4
    pdf = canvas.Canvas(output, pagesize=A4, pageCompression=1)
    pdf.setTitle(f"Party Summary - {summary.owner_name}")
    pdf.setAuthor("Little Amigos")
    margin = 24
    content_width = width - margin * 2

    pdf.setFillColor(PEACH)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(margin, height - 28, "LITTLE AMIGOS")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(margin, height - 50, "Party Summary")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawRightString(width - margin, height - 34, _safe(summary.location.name))
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(MUTED)
    pdf.drawRightString(width - margin, height - 49, f"Updated {summary.updated_at:%d %b %Y}")

    details_top = height - 66
    detail_rows = [
        (("Date", summary.party_date.strftime("%d %B %Y")), ("Party time", summary.party_time), ("Food ready", summary.food_ready)),
        (("Owner name", summary.owner_name), ("Owner number", summary.owner_number), ("Room type", summary.get_room_type_display())),
        (("Guests", f"{summary.kids_count} kids / {summary.adults_count} adults"), ("Deposit method", summary.deposit_method), ("Created by", summary.created_by.display_name)),
    ]
    col_width = content_width / 3
    detail_row_heights = []
    for row in detail_rows:
        max_lines = max(len(_wrap_lines(value, col_width - 18, size=9)) for _label, value in row)
        detail_row_heights.append(max(29, 15 + max_lines * 11))
    details_height = 31 + sum(detail_row_heights)
    _section_box(pdf, margin, details_top, content_width, details_height, "Party details")
    detail_y = details_top - 40
    for row_index, row in enumerate(detail_rows):
        for col_index, (label, value) in enumerate(row):
            _label_value(pdf, margin + 10 + col_index * col_width, detail_y, label, value, col_width - 18)
        detail_y -= detail_row_heights[row_index]

    menu_items = list(summary.menu_items.all())
    adult = [item for item in menu_items if item.category == PartyMenuItem.Category.ADULT]
    kids = [item for item in menu_items if item.category == PartyMenuItem.Category.KIDS]
    extra = [item for item in menu_items if item.category == PartyMenuItem.Category.EXTRA]
    columns_top = details_top - details_height - 10
    gap = 10
    left_width = content_width * .52
    right_width = content_width - left_width - gap
    right_x = margin + left_width + gap
    page_bottom = 24

    adult_height = 220
    _menu_column(pdf, margin, columns_top, left_width, adult_height, "Adult menu", adult)
    extra_top = columns_top - adult_height - 10
    extra_height = extra_top - page_bottom
    _extra_food_column(pdf, margin, extra_top, left_width, extra_height, extra, summary)

    kids_height = 248
    _kids_menu_column(
        pdf, right_x, columns_top, right_width, kids_height, kids,
        summary.dietary_requirements,
    )

    setup_top = columns_top - kids_height - 10
    field_width = (right_width - 30) / 2
    setup_fields = [
        ("Kids name", summary.kids_name), ("Gender", summary.get_gender_display()),
        ("Age", summary.age), ("Theme", summary.theme),
        ("Balloon color", summary.balloon_color),
    ]
    setup_rows = [setup_fields[index:index + 2] for index in range(0, len(setup_fields), 2)]
    setup_row_heights = []
    for row in setup_rows:
        max_lines = max(len(_wrap_lines(value, field_width, size=9)) for _label, value in row)
        setup_row_heights.append(max(29, 15 + max_lines * 11))
    special_note_lines = _wrap_lines(summary.special_note, right_width - 20, size=8)
    special_note_height = 17 + len(special_note_lines) * 11
    setup_height = max(148, 35 + sum(setup_row_heights) + special_note_height)
    _section_box(pdf, right_x, setup_top, right_width, setup_height, "Birthday child & setup")
    for index, (label, value) in enumerate(setup_fields):
        col = index % 2
        row = index // 2
        row_y = setup_top - 39 - sum(setup_row_heights[:row])
        _label_value(pdf, right_x + 10 + col * (field_width + 10), row_y, label, value, field_width)
    special_label_y = setup_top - 39 - sum(setup_row_heights)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 7)
    pdf.drawString(right_x + 10, special_label_y, "SPECIAL NOTE")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 8)
    _draw_wrapped(pdf, summary.special_note, right_x + 10, special_label_y - 12, right_width - 20, font_size=8)

    bill_top = setup_top - setup_height - 10
    bill_height = bill_top - page_bottom
    bill_x = right_x
    bill_width = right_width
    _section_box(pdf, bill_x, bill_top, bill_width, bill_height, "Bill")
    bill_lines = [
        ("Deposit paid", -summary.deposit_amount),
        (summary.get_package_name_display(), summary.package_amount),
        ("Extra food", summary.extra_food_total),
    ]
    if summary.food_voucher_amount:
        bill_lines.append(("Food voucher", -summary.food_voucher_amount))
    bill_lines.extend((item.name, item.amount) for item in summary.bill_items.all())
    bill_lines.append(("Other charges", summary.other_charges))
    available_bill_height = max(35, bill_height - 80)
    bill_font_size = 9
    prepared_bill_lines = []
    for candidate_size in (9, 8.5, 8, 7.5, 7, 6.5, 6, 5.5, 5):
        candidate_lines = []
        for label, amount in bill_lines:
            label_lines = _wrap_lines(label, bill_width - 72, size=candidate_size)
            candidate_lines.append((label_lines, amount, len(label_lines) * (candidate_size + 3)))
        prepared_bill_lines = candidate_lines
        bill_font_size = candidate_size
        if sum(row[2] for row in candidate_lines) <= available_bill_height:
            break
    bill_y = bill_top - 42
    pdf.setFont("Helvetica", bill_font_size)
    for label_lines, amount, row_height in prepared_bill_lines:
        pdf.setFillColor(INK)
        for index, line in enumerate(label_lines):
            pdf.drawString(bill_x + 10, bill_y - index * (bill_font_size + 3), line)
        pdf.drawRightString(bill_x + bill_width - 10, bill_y, f"${amount:,.2f}")
        bill_y -= row_height
    pdf.setFillColor(AQUA)
    pdf.roundRect(bill_x + 8, bill_top - bill_height + 10, bill_width - 16, 35, 6, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(bill_x + 16, bill_top - bill_height + 23, "TOTAL BALANCE")
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawRightString(bill_x + bill_width - 16, bill_top - bill_height + 21, f"${summary.total_balance:,.2f}")

    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica", 6)
    pdf.drawRightString(width - margin, 12, "Generated by Little Amigos Workspace")
    pdf.showPage()
    pdf.save()
    output.seek(0)
    return output
