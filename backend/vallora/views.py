from datetime import date, datetime, timedelta
from threading import Lock
from time import monotonic

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .currency import (
    convert_amount,
    format_display_amount,
    normalize_display_currency,
)
from .lodgify_client import LodgifyClient, LodgifyError, expand_availability_periods

PROPERTIES = {
    "718797": {
        "slug": "videnska",
        "name": "Vídeňská",
        "maxGuests": 6,
        "roomTypeId": "785907",
    },
    "684322": {
        "slug": "husitska",
        "name": "Husitská",
        "maxGuests": 3,
        "roomTypeId": "751369",
    },
    "508790": {
        "slug": "zikovka",
        "name": "Zikovka",
        "maxGuests": 6,
        "roomTypeId": "575343",
    },
    "507209": {
        "slug": "v-centru-deni",
        "name": "Uhelná",
        "maxGuests": 4,
        "roomTypeId": "573592",
    },
}

AVAILABILITY_DAYS = 180
AVAILABILITY_TTL_SECONDS = 10 * 60
UNAVAILABLE_MESSAGE = "Vybraný termín není dostupný."

_availability_cache = {"at": 0.0, "payload": None}
_availability_lock = Lock()

TOTAL_KEYS = (
    "total",
    "totalAmount",
    "total_amount",
    "amount",
    "total_including_vat",
    "totalIncludingVat",
    "total_with_vat",
    "amount_due",
    "amountDue",
    "grand_total",
    "grandTotal",
)


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _validate_dates(arrival, departure):
    if not arrival or not departure:
        return "Parametry arrival a departure jsou povinné."

    start = _parse_date(arrival)
    end = _parse_date(departure)

    if not start or not end:
        return "Neplatný formát data. Použijte YYYY-MM-DD."

    if end <= start:
        return "Den odjezdu musí být po dni příjezdu."

    if start < date.today():
        return "Termín příjezdu nemůže být v minulosti."

    return None


def _parse_guests(value, default=2):
    try:
        guests = int(value)
    except (TypeError, ValueError):
        guests = default

    return max(1, guests)


def _pick_amount(value):
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, dict):
        for key in TOTAL_KEYS:
            if value.get(key) is not None:
                return float(value[key])

    return None


def _extract_total(quote):
    if isinstance(quote, list):
        total = 0.0
        currency = "CZK"
        found = False

        for item in quote:
            if not isinstance(item, dict):
                continue

            amount, item_currency = _extract_total(item)

            if amount is not None:
                total += amount
                found = True
                currency = item_currency or currency

        if found:
            return total, currency

        return None, "CZK"

    if not isinstance(quote, dict):
        return None, "CZK"

    currency = (
        quote.get("currency")
        or quote.get("currencyCode")
        or quote.get("currency_code")
        or "CZK"
    )

    for key in TOTAL_KEYS:
        amount = _pick_amount(quote.get(key))
        if amount is not None:
            return amount, currency

    for nested_key in ("price", "totals", "summary", "data"):
        nested = quote.get(nested_key)
        if isinstance(nested, dict):
            amount, nested_currency = _extract_total(nested)
            if amount is not None:
                return amount, nested_currency or currency

    room_types = quote.get("room_types") or quote.get("roomTypes") or []
    room_total = 0.0
    found = False

    for room in room_types:
        if not isinstance(room, dict):
            continue

        amount = _pick_amount(room.get("total")) or _pick_amount(room.get("price"))
        if amount is not None:
            room_total += amount
            found = True

    if found:
        return room_total, currency

    return None, currency


def _format_price(amount, currency="CZK"):
    return format_display_amount(amount, currency)


def _quote_payload(
    property_id,
    meta,
    quote,
    arrival,
    departure,
    guests,
    room_type_id=None,
    display_currency="EUR",
):
    total, currency = _extract_total(quote)
    display_currency = normalize_display_currency(display_currency)

    original_total = total
    original_currency = currency

    if total is not None and display_currency != (currency or "EUR").upper():
        total = convert_amount(total, currency, display_currency, quote=quote)
        currency = display_currency

    price = {
        "total": total,
        "currency": currency,
        "formatted": _format_price(total, currency),
    }

    if original_total is not None and original_currency and original_currency.upper() != currency:
        price["originalTotal"] = original_total
        price["originalCurrency"] = original_currency

    return {
        "propertyId": property_id,
        "slug": meta["slug"],
        "name": meta["name"],
        "available": original_total is not None,
        "arrival": arrival,
        "departure": departure,
        "guests": guests,
        "price": price,
        "checkoutUrl": LodgifyClient.build_checkout_url(
            property_id,
            arrival,
            departure,
            guests,
            room_type_id,
            currency=display_currency,
        ),
        "quote": quote,
    }


def _unavailable_payload(property_id, meta, arrival, departure, guests, display_currency="CZK"):
    currency = normalize_display_currency(display_currency)
    return {
        "propertyId": property_id,
        "slug": meta["slug"],
        "name": meta["name"],
        "available": False,
        "arrival": arrival,
        "departure": departure,
        "guests": guests,
        "price": {"total": None, "currency": currency, "formatted": None},
        "checkoutUrl": None,
        "quote": None,
        "error": UNAVAILABLE_MESSAGE,
    }


def _fetch_live_availability():
    client = LodgifyClient()
    start = date.today().isoformat()
    end = (date.today() + timedelta(days=AVAILABILITY_DAYS)).isoformat()
    apartments = {}

    for property_id, meta in PROPERTIES.items():
        payload = client.get_availability(property_id, start, end)
        parsed = expand_availability_periods(payload)
        apartments[meta["slug"]] = {
            "propertyId": property_id,
            "roomTypeId": meta.get("roomTypeId"),
            "blockedDates": parsed["blockedDates"],
            "minStayByDate": parsed["minStayByDate"],
        }

    return {
        "updatedAt": timezone.now().isoformat(),
        "apartments": apartments,
    }


@require_GET
def quote_view(request):
    property_id = request.GET.get("propertyId")
    arrival = request.GET.get("arrival")
    departure = request.GET.get("departure")
    guests = _parse_guests(request.GET.get("guests"))
    room_type_id = request.GET.get("roomTypeId")
    display_currency = normalize_display_currency(request.GET.get("currency"))

    if not property_id or property_id not in PROPERTIES:
        return JsonResponse({"error": "Neznámé propertyId."}, status=400)

    date_error = _validate_dates(arrival, departure)
    if date_error:
        return JsonResponse({"error": date_error}, status=400)

    meta = PROPERTIES[property_id]

    if guests > meta["maxGuests"]:
        return JsonResponse(
            {"error": f"Tento apartmán pojme maximálně {meta['maxGuests']} hostů."},
            status=400,
        )

    try:
        client = LodgifyClient()
        room_type_id = room_type_id or meta.get("roomTypeId")
        if not room_type_id:
            room_type_id = client.get_room_type_id(property_id)

        quote = client.get_quote(property_id, arrival, departure, guests, room_type_id)
        return JsonResponse(
            _quote_payload(
                property_id,
                meta,
                quote,
                arrival,
                departure,
                guests,
                room_type_id,
                display_currency,
            )
        )
    except LodgifyError as exc:
        if exc.is_unavailable:
            return JsonResponse(
                _unavailable_payload(
                    property_id,
                    meta,
                    arrival,
                    departure,
                    guests,
                    display_currency,
                )
            )
        return JsonResponse({"error": str(exc)}, status=502)


@require_GET
def search_view(request):
    arrival = request.GET.get("arrival")
    departure = request.GET.get("departure")
    guests = _parse_guests(request.GET.get("guests"))
    display_currency = normalize_display_currency(request.GET.get("currency"))

    date_error = _validate_dates(arrival, departure)
    if date_error:
        return JsonResponse({"error": date_error}, status=400)

    results = []

    try:
        client = LodgifyClient()

        for property_id, meta in PROPERTIES.items():
            if guests > meta["maxGuests"]:
                continue

            try:
                room_type_id = meta.get("roomTypeId") or client.get_room_type_id(property_id)
                quote = client.get_quote(property_id, arrival, departure, guests, room_type_id)
                payload = _quote_payload(
                    property_id,
                    meta,
                    quote,
                    arrival,
                    departure,
                    guests,
                    room_type_id,
                    display_currency,
                )

                if payload["available"]:
                    results.append(payload)
            except LodgifyError:
                continue

        return JsonResponse(
            {
                "arrival": arrival,
                "departure": departure,
                "guests": guests,
                "results": results,
            }
        )
    except LodgifyError as exc:
        return JsonResponse({"error": str(exc)}, status=502)


@require_GET
def availability_view(_request):
    cached = None
    now = monotonic()

    with _availability_lock:
        cached = _availability_cache["payload"]
        cached_at = _availability_cache["at"]

        if cached and now - cached_at < AVAILABILITY_TTL_SECONDS:
            return JsonResponse(cached)

    try:
        payload = _fetch_live_availability()
    except LodgifyError as exc:
        if cached:
            return JsonResponse(cached)
        return JsonResponse({"error": str(exc)}, status=502)

    with _availability_lock:
        _availability_cache["at"] = monotonic()
        _availability_cache["payload"] = payload

    return JsonResponse(payload)
