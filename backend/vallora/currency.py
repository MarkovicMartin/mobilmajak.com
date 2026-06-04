import os
from decimal import Decimal, ROUND_HALF_UP

# Kalibrace z Lodgify checkout (Zikovka 11.–12. 6. 2026, 1 host):
# 149 € + 2 € → 3 605,98 + 48,40 = 3 654,38 Kč
LODGIFY_EUR_CZK = Decimal(
    os.getenv("LODGIFY_EUR_CZK", str(Decimal("3654.38") / Decimal("151")))
)


def get_lodgify_eur_czk_rate():
    return float(LODGIFY_EUR_CZK)


def normalize_display_currency(value):
    code = (value or "EUR").upper()
    return "CZK" if code == "CZK" else "EUR"


def extract_eur_line_items(quote):
    items = []
    quotes = quote if isinstance(quote, list) else [quote]

    for entry in quotes:
        if not isinstance(entry, dict):
            continue

        for room in entry.get("room_types") or entry.get("roomTypes") or []:
            if not isinstance(room, dict):
                continue

            for price_type in room.get("price_types") or room.get("priceTypes") or []:
                if not isinstance(price_type, dict):
                    continue

                sign = Decimal("-1") if price_type.get("is_negative") else Decimal("1")
                subtotal = price_type.get("subtotal")

                if subtotal is not None:
                    items.append(sign * Decimal(str(subtotal)))
                    continue

                for price in price_type.get("prices") or []:
                    if not isinstance(price, dict):
                        continue
                    amount = price.get("amount")
                    if amount is not None:
                        items.append(sign * Decimal(str(amount)))

        for addon in entry.get("add_ons") or entry.get("addOns") or []:
            if not isinstance(addon, dict):
                continue
            amount = addon.get("total") or addon.get("amount") or addon.get("price")
            if amount is not None:
                items.append(Decimal(str(amount)))

    return items


def _line_to_czk(amount_eur, rate=None):
    fx = rate or LODGIFY_EUR_CZK
    return (amount_eur * fx).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def convert_eur_lines_to_czk(lines, rate=None):
    if not lines:
        return None

    total = sum(_line_to_czk(line, rate) for line in lines)
    return float(total)


def convert_quote_to_czk(quote, rate=None):
    lines = extract_eur_line_items(quote)
    if lines:
        return convert_eur_lines_to_czk(lines, rate)

    return None


def convert_amount(amount, from_currency, to_currency, quote=None):
    if amount is None:
        return None

    from_code = (from_currency or "EUR").upper()
    to_code = (to_currency or from_code).upper()

    if from_code == to_code:
        return float(amount)

    value = Decimal(str(amount))

    if from_code == "EUR" and to_code == "CZK":
        if quote is not None:
            converted = convert_quote_to_czk(quote)
            if converted is not None:
                return converted

        return float(_line_to_czk(value))

    if from_code == "CZK" and to_code == "EUR":
        return float((value / LODGIFY_EUR_CZK).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    return float(value)


def format_display_amount(amount, currency="CZK"):
    if amount is None:
        return None

    code = (currency or "CZK").upper()
    value = Decimal(str(amount))

    if code == "CZK":
        rounded = value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        text = f"{rounded:,}".replace(",", " ")
        return f"{text} Kč"

    if value == value.to_integral_value():
        return f"{int(value):,} {code}".replace(",", " ")

    return f"{float(value):,.2f} {code}".replace(",", " ")
