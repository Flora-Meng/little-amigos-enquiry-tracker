from io import BytesIO

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
            if len(shown) > max_chars:
                shown = shown[: max_chars - 3] + "..."
            commands.extend(["BT", f"/F1 {font_size:.2f} Tf", f"32 {y:.2f} Td", f"({_pdf_escape(shown)}) Tj", "ET"])
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


def _label_value(pdf, x, y, label, value, width, font_size=8):
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.setFillColor(MUTED)
    pdf.drawString(x, y, label.upper())
    pdf.setFont("Helvetica", font_size)
    pdf.setFillColor(INK)
    pdf.drawString(x, y - 11, _fit(value, width, size=font_size))


def _section_box(pdf, x, top, width, height, title):
    bottom = top - height
    pdf.setStrokeColor(BORDER)
    pdf.setFillColor(colors.white)
    pdf.roundRect(x, bottom, width, height, 8, fill=1, stroke=1)
    pdf.setFillColor(PALE)
    pdf.roundRect(x, top - 24, width, 24, 8, fill=1, stroke=0)
    pdf.rect(x, top - 24, width, 8, fill=1, stroke=0)
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(x + 10, top - 16, title)
    return bottom


def _menu_column(pdf, x, top, width, height, title, items, show_amount=False):
    _section_box(pdf, x, top, width, height, title)
    rows = max(len(items), 1)
    row_height = min(15, max(7, (height - 30) / rows))
    font_size = min(8, max(5.5, row_height - 3.5))
    y = top - 34
    for item in items[:20]:
        qty_width = 48
        amount_width = 42 if show_amount else 0
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawString(x + 8, y, _fit(item.quantity, qty_width - 4, "Helvetica-Bold", font_size))
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        item_width = width - qty_width - amount_width - 18
        item_text = f"{item.item} - {item.notes}" if item.notes else item.item
        pdf.drawString(x + qty_width + 5, y, _fit(item_text, item_width, size=font_size))
        if show_amount:
            pdf.drawRightString(x + width - 8, y, f"${item.amount:,.2f}")
        y -= row_height


def _kids_menu_column(pdf, x, top, width, height, items, dietary_requirements):
    _section_box(pdf, x, top, width, height, "Kids menu - 1 drink per child")
    dietary_height = 67
    menu_bottom = top - height + dietary_height
    available_height = max(48, top - 30 - menu_bottom)
    rows = max(len(items), 1)
    row_height = min(16, max(8, available_height / rows))
    font_size = min(8.5, max(6, row_height - 4))
    y = top - 37
    for item in items[:20]:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawString(x + 10, y, _fit(item.quantity, 35, "Helvetica-Bold", font_size))
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        item_text = f"{item.item} - {item.notes}" if item.notes else item.item
        pdf.drawString(x + 49, y, _fit(item_text, width - 61, size=font_size))
        y -= row_height
    divider_y = top - height + dietary_height
    pdf.setStrokeColor(BORDER)
    pdf.line(x + 10, divider_y, x + width - 10, divider_y)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawString(x + 10, divider_y - 15, "DIETARY REQUIREMENTS")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 7.5)
    _draw_wrapped(
        pdf, dietary_requirements or "None advised", x + 10, divider_y - 29,
        width - 20, max_lines=3, font_size=7.5,
    )


def _extra_food_column(pdf, x, top, width, height, items, summary):
    _section_box(pdf, x, top, width, height, "Extra food")
    image_data = bytes(summary.decoration_example or b"")
    image_label_height = 18 if image_data else 0
    image_area_height = min(205, max(0, height * .56)) if image_data else 0
    menu_area_height = height - 29 - image_area_height - image_label_height
    rows = max(len(items), 1)
    row_height = min(15, max(7, menu_area_height / rows))
    font_size = min(8, max(5.5, row_height - 3.5))
    y = top - 37
    for item in items[:20]:
        pdf.setFillColor(MUTED)
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawString(x + 10, y, _fit(item.quantity, 32, "Helvetica-Bold", font_size))
        pdf.setFillColor(INK)
        pdf.setFont("Helvetica", font_size)
        item_text = f"{item.item} - {item.notes}" if item.notes else item.item
        pdf.drawString(x + 47, y, _fit(item_text, width - 105, size=font_size))
        pdf.drawRightString(x + width - 10, y, f"${item.amount:,.2f}")
        y -= row_height
    if not image_data:
        return
    label_y = top - height + image_area_height + 7
    pdf.setStrokeColor(BORDER)
    pdf.line(x + 10, label_y + 10, x + width - 10, label_y + 10)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 6.5)
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


def _draw_wrapped(pdf, text, x, y, width, max_lines=4, font_size=7):
    words = _safe(text).split()
    lines = []
    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if stringWidth(candidate, "Helvetica", font_size) <= width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
        if len(lines) == max_lines:
            break
    if line and len(lines) < max_lines:
        lines.append(line)
    for index, value in enumerate(lines[:max_lines]):
        if index == max_lines - 1 and len(words) > sum(len(item.split()) for item in lines):
            value = _fit(value + "...", width, size=font_size)
        pdf.drawString(x, y - index * (font_size + 3), value)


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
    details_height = 112
    _section_box(pdf, margin, details_top, content_width, details_height, "Party details")
    detail_rows = [
        (("Date", summary.party_date.strftime("%d %B %Y")), ("Party time", summary.party_time), ("Food ready", summary.food_ready)),
        (("Owner name", summary.owner_name), ("Owner number", summary.owner_number), ("Room type", summary.get_room_type_display())),
        (("Guests", f"{summary.kids_count} kids / {summary.adults_count} adults"), ("Deposit method", summary.deposit_method), ("Created by", summary.created_by.display_name)),
    ]
    col_width = content_width / 3
    for row_index, row in enumerate(detail_rows):
        y = details_top - 40 - row_index * 27
        for col_index, (label, value) in enumerate(row):
            _label_value(pdf, margin + 10 + col_index * col_width, y, label, value, col_width - 18)

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
    setup_height = 148
    _section_box(pdf, right_x, setup_top, right_width, setup_height, "Birthday child & setup")
    field_width = (right_width - 30) / 2
    setup_fields = [
        ("Kids name", summary.kids_name), ("Gender", summary.get_gender_display()),
        ("Age", summary.age), ("Theme", summary.theme),
        ("Balloon color", summary.balloon_color),
    ]
    for index, (label, value) in enumerate(setup_fields):
        col = index % 2
        row = index // 2
        _label_value(pdf, right_x + 10 + col * (field_width + 10), setup_top - 39 - row * 27, label, value, field_width)
    pdf.setFillColor(MUTED)
    pdf.setFont("Helvetica-Bold", 6.5)
    pdf.drawString(right_x + 10, setup_top - 116, "SPECIAL NOTE")
    pdf.setFillColor(INK)
    pdf.setFont("Helvetica", 7)
    _draw_wrapped(pdf, summary.special_note, right_x + 10, setup_top - 128, right_width - 20, max_lines=2)

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
    bill_gap = min(19, max(10, available_bill_height / max(len(bill_lines), 1)))
    bill_font_size = min(7.5, max(6, bill_gap - 4))
    bill_y = bill_top - 42
    pdf.setFont("Helvetica", bill_font_size)
    for label, amount in bill_lines:
        pdf.setFillColor(INK)
        pdf.drawString(bill_x + 10, bill_y, _fit(label, bill_width - 72, size=bill_font_size))
        pdf.drawRightString(bill_x + bill_width - 10, bill_y, f"${amount:,.2f}")
        bill_y -= bill_gap
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
