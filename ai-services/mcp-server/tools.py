"""Deterministic MCP tools shared across student microservices."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


class ToolError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _require(args: dict[str, Any], name: str) -> Any:
    if name not in args or args[name] in (None, ""):
        raise ToolError(f"Missing required argument: {name}")
    return args[name]


def _parse_date(value: Any, field: str) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise ToolError(f"{field} must be an ISO date (YYYY-MM-DD)") from exc


def days_until_departure(args: dict[str, Any]) -> dict[str, Any]:
    departure = _parse_date(_require(args, "departure_date"), "departure_date")
    today = date.today()
    days = (departure - today).days
    return {
        "departure_date": departure.isoformat(),
        "today": today.isoformat(),
        "days_until_departure": days,
        "has_departed": days < 0,
    }


def passport_validity_check(args: dict[str, Any]) -> dict[str, Any]:
    expiry = _parse_date(_require(args, "expiry_date"), "expiry_date")
    return_date = _parse_date(_require(args, "return_date"), "return_date")
    try:
        minimum_validity_days = int(args.get("minimum_validity_days") or 0)
    except (TypeError, ValueError) as exc:
        raise ToolError("minimum_validity_days must be a whole number") from exc
    margin_days = (expiry - return_date).days
    return {
        "expiry_date": expiry.isoformat(),
        "return_date": return_date.isoformat(),
        "minimum_validity_days": minimum_validity_days,
        "margin_days": margin_days,
        "meets_minimum_validity": margin_days >= minimum_validity_days,
        "is_expired_by_return": margin_days < 0,
    }


_CLIMATE_TIPS = {
    "hot": "Pack lightweight breathable clothing, sun protection and extra water.",
    "cold": "Pack thermal layers, insulated outerwear and waterproof footwear.",
    "rainy": "Pack a waterproof jacket, quick-dry clothing and a compact umbrella.",
    "mild": "Pack layered clothing to adapt to changing daytime and evening temperatures.",
    "humid": "Pack breathable fabrics and moisture-wicking clothing.",
    "dry": "Pack moisturiser, lip balm and a reusable water bottle.",
}


def packing_climate_tip(args: dict[str, Any]) -> dict[str, Any]:
    climate = str(_require(args, "climate")).strip().lower()
    tip = _CLIMATE_TIPS.get(climate)
    if not tip:
        return {
            "climate": climate,
            "tip": "No specific guidance for this climate; pack versatile layers and check the forecast closer to departure.",
            "matched": False,
        }
    return {"climate": climate, "tip": tip, "matched": True}


TOOLS: dict[str, dict[str, Any]] = {
    "days_until_departure": {
        "description": "Calculate how many days remain until a trip's departure date.",
        "arguments": ["departure_date"],
        "handler": days_until_departure,
    },
    "passport_validity_check": {
        "description": (
            "Check whether a passport's expiry date meets a minimum validity requirement for the return date."
        ),
        "arguments": ["expiry_date", "return_date", "minimum_validity_days"],
        "handler": passport_validity_check,
    },
    "packing_climate_tip": {
        "description": "Get a deterministic packing tip for a given climate.",
        "arguments": ["climate"],
        "handler": packing_climate_tip,
    },
}
