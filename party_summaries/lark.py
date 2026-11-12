"""Server-side Lark Base synchronisation for weekly party uploads."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
import json
import time as time_module
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone

from .models import PartyMenuItem, menu_quantity_number


LARK_API_ROOT = "https://open.larksuite.com/open-apis"
READ_ONLY_FIELD_TYPES = {19, 20, 1001, 1002, 1003, 1004, 1005}
LINK_FIELD_TYPES = {18, 21}
UNSUPPORTED_DIRECT_WRITE_FIELD_TYPES = {11, 17, *LINK_FIELD_TYPES, 22, 23}

# Party summaries keep the customer-facing wording that staff already use.  The
# Lark Menu has a few different canonical names, so translate only at sync time.
# Keys and values are normalised by ``_normalise_field_name`` before matching.
LARK_MENU_ITEM_ALIASES = {
    "Kid spaghetti": "Kid Sphagetti",
    "Mixed Fryer platter": "Mixed fryer platter (assorted)",
    "Mix Fryer platter": "Mixed fryer platter (assorted)",
    "Vege Fryer Platter": "Mixed fryer platter (vege)",
    "Mix Fryer platter (Vege)": "Mixed fryer platter (vege)",
    "Pizza (Margherita, 10-inch)": "Pizza (Margherita)",
    "Pizza (Pepperoni, 10-inch)": "Pizza (Pepperoni)",
    "Pizza (Vegetarian, 10-inch)": "Pizza (Vege)",
    "Pizza (Cheese, 10-inch)": "Pizza (Cheese)",
    "Pizza (Vegetarian)": "Pizza (Vege)",
    "Caesar salad bowl": "Caesar chicken salad",
    "Mini burger platter 10pcs (Pork)": "Mini burger sliders 10pcs (Pork)",
    "Mini burger platter 10pcs (Prawn)": "Mini burger sliders 10pcs (Prawn)",
    "Mini burger platter 10pcs (Vegetarian)": "Mini burger sliders 10pcs (Vege)",
    "Mini burger 10pcs (Pork)": "Mini burger sliders 10pcs (Pork)",
    "Mini burger 10pcs (Prawn)": "Mini burger sliders 10pcs (Prawn)",
    "Mini burger 10pcs (Vege)": "Mini burger sliders 10pcs (Vege)",
    "Smoked salmon toast 12pcs": "Smoked Salmon Avocado Toast 10pcs",
    "Mushroom toast 12pcs (vegetarian)": "Millennial Mushroom Toast 10pcs",
    "Japanese sushi platter (vegetarian)": "Japanese sushi platter (vege)",
    "Mini burger sliders 10pcs (Chicken)": "Mini Burger Sliders (Chicken)",
    "Mini burger sliders 10pcs (Beef)": "Mini Burger Sliders (Beef)",
    "Grilled Salmon Platter": "Grilled salmon platter 10pcs",
    "Grilled Beef Skewer platter": "Grilled Beef Skewer platter 10pcs",
    "Beef Bolognese Spaghetti": "Beef Ragu Spaghetti",
    "Finger Sandwiches 16pcs (Egg)": "Finger Sandwiches 16pcs (Eggs)",
    "Seasonal fruit platter": "Fruit Platter",
    "Soft drinks / juice": "Jug of Drink",
    "Refillable water": "Drink",
    "Water": "Drink",
    "Kids' size drink": "Kid Juice",
}


class LarkConfigurationError(RuntimeError):
    pass


class LarkAPIError(RuntimeError):
    pass


def lark_is_configured():
    return bool(settings.LARK_APP_ID and settings.LARK_APP_SECRET)


def _request(method, path, *, token=None, payload=None, query=None):
    url = f"{LARK_API_ROOT}{path}"
    if query:
        url += "?" + urlencode(query)
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise LarkAPIError(f"Lark returned HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise LarkAPIError(f"Could not reach Lark: {error}") from error
    if body.get("code", 0) != 0:
        raise LarkAPIError(f"Lark error {body.get('code')}: {body.get('msg', 'Unknown error')}")
    return body.get("data") or body


class LarkBaseClient:
    def __init__(self):
        if not lark_is_configured():
            raise LarkConfigurationError(
                "Lark is not connected yet. Add LARK_APP_ID and LARK_APP_SECRET in Render."
            )
        self.app_token = settings.LARK_PARTY_BASE_TOKEN
        self.order_table_id = settings.LARK_ORDER_TABLE_ID
        self.food_table_id = settings.LARK_FOOD_ORDER_TABLE_ID
        self.token = self._tenant_token()

    def _tenant_token(self):
        data = _request("POST", "/auth/v3/tenant_access_token/internal", payload={
            "app_id": settings.LARK_APP_ID,
            "app_secret": settings.LARK_APP_SECRET,
        })
        token = data.get("tenant_access_token")
        if not token:
            raise LarkAPIError("Lark did not return a tenant access token.")
        return token

    def fields(self, table_id):
        items = []
        page_token = ""
        while True:
            query = {"page_size": 100}
            if page_token:
                query["page_token"] = page_token
            data = _request(
                "GET",
                f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/fields",
                token=self.token,
                query=query,
            )
            items.extend(data.get("items") or [])
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token") or ""

    def tables(self):
        items = []
        page_token = ""
        while True:
            query = {"page_size": 100}
            if page_token:
                query["page_token"] = page_token
            data = _request(
                "GET", f"/bitable/v1/apps/{self.app_token}/tables",
                token=self.token, query=query,
            )
            items.extend(data.get("items") or [])
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token") or ""

    def records(self, table_id):
        items = []
        page_token = ""
        while True:
            query = {"page_size": 500}
            if page_token:
                query["page_token"] = page_token
            data = _request(
                "GET",
                f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records",
                token=self.token, query=query,
            )
            items.extend(data.get("items") or [])
            if not data.get("has_more"):
                return items
            page_token = data.get("page_token") or ""

    def create_records(self, table_id, records):
        created = []
        for index in range(0, len(records), 500):
            data = _request(
                "POST",
                f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create",
                token=self.token,
                payload={"records": [{"fields": record} for record in records[index:index + 500]]},
            )
            created.extend(data.get("records") or [])
        return created

    def get_record(self, table_id, record_id):
        data = _request(
            "GET",
            f"/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{record_id}",
            token=self.token,
        )
        return data.get("record") or {}


def _normalise_field_name(value):
    return "".join(character for character in (value or "").casefold() if character.isalnum())


NORMALISED_LARK_MENU_ITEM_ALIASES = {
    _normalise_field_name(source): _normalise_field_name(target)
    for source, target in LARK_MENU_ITEM_ALIASES.items()
}


def _normalise_menu_item_name(value):
    name = _normalise_field_name(value)
    return NORMALISED_LARK_MENU_ITEM_ALIASES.get(name, name)


def _field_catalog(field_items):
    return {
        _normalise_field_name(item.get("field_name")): item
        for item in field_items
        if item.get("field_name")
    }


def _resolve_field(catalog, aliases, *, writable_only=True):
    for alias in aliases:
        item = catalog.get(_normalise_field_name(alias))
        if item and (not writable_only or item.get("type") not in READ_ONLY_FIELD_TYPES):
            return item
    return None


def _date_value(field, value):
    if field and field.get("type") == 5:
        moment = datetime.combine(value, time.min, tzinfo=timezone.get_current_timezone())
        return int(moment.timestamp() * 1000)
    return value.isoformat()


def _field_value(field, value):
    """Convert ordinary Python values to the shape expected by a Base field."""
    field_type = field.get("type")
    if field_type in UNSUPPORTED_DIRECT_WRITE_FIELD_TYPES:
        return None
    if field_type in {1, 13}:
        return str(value)
    if field_type == 2:
        return float(value)
    if field_type == 3:
        return str(value)
    if field_type == 4:
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value]
        return [str(value)]
    if field_type == 5 and hasattr(value, "isoformat"):
        return _date_value(field, value)
    if field_type == 7:
        return bool(value)
    if field_type == 15:
        text = str(value)
        return {"text": text, "link": text}
    return value


def _put(fields, catalog, aliases, value):
    field = _resolve_field(catalog, aliases)
    if field is not None and value is not None:
        converted = _field_value(field, value)
        if converted is not None:
            fields[field["field_name"]] = converted
    return field


def _short_store_name(summary):
    name = summary.location.name.removeprefix("Little Amigos ").strip()
    return "DFO" if name.casefold() == "canberra" else name


def _order_fields(summary, catalog):
    fields = {}
    _put(fields, catalog, ("Party ID",), str(summary.id))
    _put(fields, catalog, ("Store", "Location"), _short_store_name(summary))
    date_field = _resolve_field(catalog, ("Date", "Party Date"))
    if date_field:
        fields[date_field["field_name"]] = _date_value(date_field, summary.party_date)
    _put(fields, catalog, ("Owner Name", "Customer Name", "Name"), summary.owner_name)
    _put(fields, catalog, ("Time", "Party Time"), summary.party_time)
    _put(fields, catalog, ("Room Type", "Room"), summary.get_room_type_display())
    _put(fields, catalog, ("Deposit",), float(summary.deposit_amount))
    _put(fields, catalog, ("Deposit Method", "Payment Method"), summary.deposit_method)
    _put(fields, catalog, ("Balance", "Actual Balance"), float(summary.actual_balance))
    _put(fields, catalog, ("Total", "Total Invoice", "Total Invoiced"), float(summary.total_invoiced))
    return fields


def _line_amounts(item):
    quantity = menu_quantity_number(item.quantity)
    if quantity <= 0:
        quantity = Decimal("1")
    if item.category == PartyMenuItem.Category.EXTRA:
        line_total = item.amount
        unit_price = item.amount / quantity
    else:
        unit_price = item.amount
        line_total = item.amount * quantity
    return quantity, unit_price, line_total


def _voucher_package_item_ids(summary, items):
    """Choose whole food rows whose totals are closest to the voucher allowance."""
    if not summary.uses_food_voucher:
        return set()
    priced = []
    for item in items:
        _, _, line_total = _line_amounts(item)
        if line_total > 0:
            priced.append((item.id, int((line_total * 100).quantize(Decimal("1")))))
    target = int((summary.food_voucher_amount * 100).quantize(Decimal("1")))
    if not priced or target <= 0:
        return set()
    ceiling = target + max(amount for _, amount in priced)
    combinations = {0: ()}
    for item_id, amount in priced:
        for subtotal, selected in list(combinations.items()):
            candidate = subtotal + amount
            if candidate <= ceiling and candidate not in combinations:
                combinations[candidate] = selected + (item_id,)
    best = min(combinations, key=lambda subtotal: (
        abs(subtotal - target), subtotal > target, -subtotal,
    ))
    return set(combinations[best])


def _food_tag(summary, item, line_total, voucher_package_ids):
    if item.category == PartyMenuItem.Category.EXTRA:
        return "Free" if line_total == 0 else "Extra"
    if summary.uses_food_voucher:
        return "Package" if line_total == 0 or item.id in voucher_package_ids else "Extra"
    return "Package"


def _display_value(value):
    if isinstance(value, list):
        return " ".join(_display_value(item) for item in value)
    if isinstance(value, dict):
        return str(
            value.get("text") or value.get("name") or value.get("value") or ""
        )
    return "" if value is None else str(value)


def _menu_record_ids(client, food_catalog, items, store_name):
    item_field = _resolve_field(food_catalog, ("Item", "Food", "Food Item"))
    if not item_field or item_field.get("type") not in LINK_FIELD_TYPES:
        return {}

    menu_table = next(
        (
            table for table in client.tables()
            if _normalise_field_name(table.get("name")) == "menu"
        ),
        None,
    )
    if not menu_table:
        raise LarkAPIError("The Lark Base has no table named Menu.")
    menu_table_id = menu_table.get("table_id")
    menu_fields = client.fields(menu_table_id)
    primary = next(
        (field for field in menu_fields if field.get("is_primary")),
        None,
    ) or _resolve_field(
        _field_catalog(menu_fields), ("Item", "Food", "Menu", "Name"),
        writable_only=False,
    )
    if not primary:
        raise LarkAPIError("The Lark Menu table has no identifiable item-name field.")
    store_field = _resolve_field(
        _field_catalog(menu_fields), ("Store", "Location"), writable_only=False,
    )

    by_item = {}
    by_item_and_store = {}
    for record in client.records(menu_table_id):
        values = record.get("fields") or {}
        item_name = _normalise_field_name(_display_value(values.get(primary["field_name"])))
        if not item_name:
            continue
        record_id = record.get("record_id")
        by_item.setdefault(item_name, record_id)
        if store_field:
            record_store = _normalise_field_name(
                _display_value(values.get(store_field["field_name"]))
            )
            by_item_and_store.setdefault((item_name, record_store), record_id)

    wanted_store = _normalise_field_name(store_name)
    matched = {}
    missing = []
    for item in items:
        name = _normalise_menu_item_name(item.item)
        record_id = by_item_and_store.get((name, wanted_store)) or by_item.get(name)
        if record_id:
            matched[item.id] = record_id
        else:
            missing.append(item.item)
    if missing:
        names = ", ".join(dict.fromkeys(missing))
        raise LarkAPIError(f"These food items were not found in the Lark Menu: {names}")
    return matched


def _put_link_or_value(fields, catalog, aliases, value, record_id=None):
    field = _resolve_field(catalog, aliases)
    if not field:
        return None
    if field.get("type") in LINK_FIELD_TYPES:
        if record_id:
            fields[field["field_name"]] = [record_id]
        return field
    converted = _field_value(field, value)
    if converted is not None:
        fields[field["field_name"]] = converted
    return field


def _food_fields(
    summary, item, catalog, party_id, tag, *, order_record_id=None,
    menu_record_id=None,
):
    fields = {}
    quantity, unit_price, line_total = _line_amounts(item)
    _put_link_or_value(
        fields, catalog, ("Party ID",), party_id, record_id=order_record_id,
    )
    _put(fields, catalog, ("Store", "Location"), _short_store_name(summary))
    date_field = _resolve_field(catalog, ("Date", "Party Date"))
    if date_field:
        fields[date_field["field_name"]] = _date_value(date_field, summary.party_date)
    _put_link_or_value(
        fields, catalog, ("Item", "Food", "Food Item"), item.item,
        record_id=menu_record_id,
    )
    _put(fields, catalog, ("Food Notes", "Item Notes", "Notes"), item.notes)
    _put(fields, catalog, ("Qty", "Quantity"), float(quantity))
    _put(fields, catalog, ("Price", "Unit Price"), float(unit_price))
    if not menu_record_id:
        _put(fields, catalog, ("One-off Price", "One Off Price"), float(unit_price))
    _put(fields, catalog, ("Amount", "Line Total"), float(line_total))
    _put(
        fields, catalog,
        ("Tag", "Type", "Food Type", "Food Category", "Package / Extra", "Note"),
        tag,
    )
    return fields


def _party_id_from_record(client, summary, order_catalog):
    writable_party_id = _resolve_field(order_catalog, ("Party ID",))
    if writable_party_id:
        return str(summary.id)
    for attempt in range(3):
        record = client.get_record(client.order_table_id, summary.lark_order_record_id)
        value = (record.get("fields") or {}).get("Party ID")
        if isinstance(value, list):
            value = "".join(
                str(part.get("text", part)) if isinstance(part, dict) else str(part)
                for part in value
            )
        elif isinstance(value, dict):
            value = value.get("text") or value.get("value") or value.get("name")
        if value not in (None, ""):
            return str(value)
        if attempt < 2:
            time_module.sleep(0.4)
    raise LarkAPIError("The Lark Order record was created, but its Party ID formula is still empty.")


def sync_summaries_to_lark(summaries, *, client=None):
    """Upload selected parties once and return a compact per-batch result."""
    client = client or LarkBaseClient()
    order_catalog = _field_catalog(client.fields(client.order_table_id))
    food_catalog = _field_catalog(client.fields(client.food_table_id))
    if not _resolve_field(order_catalog, ("Owner Name", "Customer Name", "Name")):
        raise LarkAPIError("The Lark Order table has no writable customer name field.")
    if not _resolve_field(food_catalog, ("Item", "Food", "Food Item")):
        raise LarkAPIError("The Lark Food Order table has no writable Item field.")

    result = {"uploaded": 0, "skipped": 0, "failed": 0, "errors": []}
    for summary in summaries:
        if summary.lark_synced_at:
            result["skipped"] += 1
            continue
        try:
            if not summary.lark_order_record_id:
                created = client.create_records(
                    client.order_table_id, [_order_fields(summary, order_catalog)],
                )
                if not created or not created[0].get("record_id"):
                    raise LarkAPIError("Lark did not return the new Order record ID.")
                summary.lark_order_record_id = created[0]["record_id"]
                summary.lark_sync_error = ""
                summary.save(update_fields=("lark_order_record_id", "lark_sync_error", "updated_at"))

            party_id = summary.lark_party_id or _party_id_from_record(
                client, summary, order_catalog,
            )
            if summary.lark_party_id != party_id:
                summary.lark_party_id = party_id
                summary.save(update_fields=("lark_party_id", "updated_at"))

            items = list(summary.menu_items.all())
            voucher_package_ids = _voucher_package_item_ids(summary, items)
            menu_record_ids = _menu_record_ids(
                client, food_catalog, items, _short_store_name(summary),
            )
            food_records = []
            for item in items:
                _, _, line_total = _line_amounts(item)
                tag = _food_tag(summary, item, line_total, voucher_package_ids)
                food_records.append(_food_fields(
                    summary, item, food_catalog, party_id, tag,
                    order_record_id=summary.lark_order_record_id,
                    menu_record_id=menu_record_ids.get(item.id),
                ))
            if food_records:
                client.create_records(client.food_table_id, food_records)

            summary.lark_synced_at = timezone.now()
            summary.lark_sync_error = ""
            summary.save(update_fields=("lark_synced_at", "lark_sync_error", "updated_at"))
            result["uploaded"] += 1
        except (LarkAPIError, LarkConfigurationError) as error:
            summary.lark_sync_error = str(error)[:2000]
            summary.save(update_fields=("lark_sync_error", "updated_at"))
            result["failed"] += 1
            result["errors"].append(f"{summary.owner_name}: {error}")
    return result
