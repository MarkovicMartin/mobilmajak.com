import json
import os
from datetime import date, timedelta
from urllib.parse import urlencode

import requests


class LodgifyError(Exception):
    def __init__(self, message, status_code=None, payload=None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload if isinstance(payload, dict) else {}

    @property
    def is_unavailable(self):
        code = self.payload.get("code")
        message = str(self.payload.get("message") or self.args[0] or "").lower()
        return (
            code == 666
            or code == "666"
            or "already booked" in message
            or "not available" in message
        )


class LodgifyClient:
    BASE_URL = "https://api.lodgify.com/v2"
    CHECKOUT_BASE = "https://checkout.lodgify.com/cs/vallora"

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("LODGIFY_API_KEY")

        if not self.api_key:
            raise LodgifyError("LODGIFY_API_KEY is not configured")

    def _headers(self):
        return {
            "X-ApiKey": self.api_key,
            "Accept": "application/json",
        }

    def _get(self, path, params=None):
        response = requests.get(
            f"{self.BASE_URL}{path}",
            headers=self._headers(),
            params=params or {},
            timeout=15,
        )

        if not response.ok:
            payload = {}
            try:
                payload = response.json()
            except (ValueError, json.JSONDecodeError):
                payload = {}

            raise LodgifyError(
                f"Lodgify API {response.status_code}: {response.text[:300]}",
                status_code=response.status_code,
                payload=payload,
            )

        return response.json()

    def get_property(self, property_id):
        return self._get(f"/properties/{property_id}")

    def get_room_type_id(self, property_id):
        property_data = self.get_property(property_id)
        rooms = (
            property_data.get("rooms")
            or property_data.get("roomTypes")
            or property_data.get("room_types")
            or []
        )

        if not rooms:
            return None

        room = rooms[0]
        room_type_id = room.get("id") or room.get("room_type_id") or room.get("roomTypeId")
        return str(room_type_id) if room_type_id is not None else None

    def get_quote(self, property_id, arrival, departure, guests, room_type_id=None):
        params = {
            "arrival": arrival,
            "departure": departure,
            "from": arrival,
            "to": departure,
            "roomTypes[0].people": guests,
            "guest_breakdown[adults]": guests,
        }

        if room_type_id:
            params["roomTypes[0].id"] = room_type_id
            params["roomTypes[0].Id"] = room_type_id

        return self._get(f"/quote/{property_id}", params)

    def get_availability(self, property_id, start, end):
        return self._get(f"/availability/{property_id}", {"start": start, "end": end})

    @classmethod
    def build_checkout_url(
        cls, property_id, arrival, departure, guests, room_type_id=None, currency="CZK"
    ):
        params = {
            "currency": currency or "CZK",
            "arrival": arrival,
            "departure": departure,
            "guests": guests,
            "adults": guests,
            "numberOfGuests": guests,
        }

        if room_type_id:
            params["roomTypeId"] = room_type_id

        query = urlencode(params)
        return f"{cls.CHECKOUT_BASE}/{property_id}/reservation?{query}"


def _period_available(period):
    value = period.get("available")
    return value in (1, True, "1")


def _read_min_stay(entry):
    raw = (
        entry.get("min_stay")
        if isinstance(entry, dict)
        else None
    )
    if raw is None and isinstance(entry, dict):
        raw = (
            entry.get("minStay")
            or entry.get("minimum_stay")
            or entry.get("MinimumStay")
            or entry.get("minimumStay")
        )

    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None

    return value if value > 0 else None


def expand_availability_periods(payload):
    """Lodgify end = last occupied night (inclusive). Checkout day is the day after end."""
    blocked = set()
    min_stay_by_date = {}
    details = payload if isinstance(payload, list) else payload.get("details") or [payload]

    for entry in details:
        if not isinstance(entry, dict):
            continue

        for period in entry.get("periods") or []:
            if not isinstance(period, dict) or not period.get("start") or not period.get("end"):
                continue

            start = date.fromisoformat(period["start"][:10])
            end = date.fromisoformat(period["end"][:10])
            min_stay = _read_min_stay(period)
            available = _period_available(period)
            current = start

            while current <= end:
                key = current.isoformat()
                if not available:
                    blocked.add(key)
                if min_stay:
                    min_stay_by_date[key] = max(min_stay_by_date.get(key, 0), min_stay)
                current += timedelta(days=1)

    return {
        "blockedDates": sorted(blocked),
        "minStayByDate": min_stay_by_date,
    }
