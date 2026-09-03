from __future__ import annotations

import re
from typing import Any

from config import (
    ACCESSIBILITY_REQUIREMENTS,
    CURRENCIES,
    DIETARY_RESTRICTIONS,
    INTEREST_CATEGORIES,
    PACES,
    PRIORITIES,
    TRAVEL_STYLES,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ValidationError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


def require_object(payload: Any) -> dict[str, Any]:
    if payload is None:
        raise ValidationError("Malformed JSON", 400)
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object", 400)
    return payload


def require_non_empty(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field} is required")
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")
    return value.strip()


def require_email(payload: dict[str, Any], field: str = "email") -> str:
    value = require_non_empty(payload, field)
    if not EMAIL_RE.match(value):
        raise ValidationError(f"{field} must be a valid email address")
    return value.lower()


def require_choice(payload: dict[str, Any], field: str, allowed: tuple[str, ...]) -> str:
    value = require_non_empty(payload, field)
    if value not in allowed:
        raise ValidationError(f"{field} must be one of: {', '.join(allowed)}")
    return value


def require_int(payload: dict[str, Any], field: str, minimum: int | None = None) -> int:
    if field not in payload:
        raise ValidationError(f"{field} is required")
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        if isinstance(value, str) and value.strip().isdigit():
            value = int(value)
        else:
            raise ValidationError(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{field} must be at least {minimum}")
    return int(value)


def require_number(payload: dict[str, Any], field: str, minimum: float | None = None) -> float:
    if field not in payload:
        raise ValidationError(f"{field} is required")
    value = payload[field]
    if isinstance(value, bool):
        raise ValidationError(f"{field} must be a number")
    if isinstance(value, str):
        try:
            value = float(value.strip())
        except ValueError as exc:
            raise ValidationError(f"{field} must be a number") from exc
    if not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number")
    if minimum is not None and value < minimum:
        raise ValidationError(f"{field} must be at least {minimum}")
    return float(value)


def parse_id(record_id: str | int) -> int:
    try:
        value = int(record_id)
    except (TypeError, ValueError) as exc:
        raise ValidationError("id must be a valid integer") from exc
    if value <= 0:
        raise ValidationError("id must be a valid integer")
    return value


def validate_traveler(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not partial or "full_name" in payload:
        data["full_name"] = require_non_empty(payload, "full_name")
    if not partial or "username" in payload:
        data["username"] = require_non_empty(payload, "username")
    if not partial or "email" in payload:
        data["email"] = require_email(payload, "email")
    if not partial or "home_location" in payload:
        data["home_location"] = require_non_empty(payload, "home_location")
    if not partial or "travel_style" in payload:
        data["travel_style"] = require_choice(payload, "travel_style", TRAVEL_STYLES)
    return data


def validate_preference(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not partial or "traveler_id" in payload:
        data["traveler_id"] = require_int(payload, "traveler_id", minimum=1)
    if not partial or "budget_min" in payload:
        data["budget_min"] = require_number(payload, "budget_min", minimum=0)
    if not partial or "budget_max" in payload:
        data["budget_max"] = require_number(payload, "budget_max", minimum=0)
    if "currency" in payload:
        data["currency"] = require_choice(payload, "currency", CURRENCIES)
    elif not partial:
        data["currency"] = "AUD"
    if not partial or "pace" in payload:
        data["pace"] = require_choice(payload, "pace", PACES)
    if "preferred_trip_length_days" in payload:
        value = payload["preferred_trip_length_days"]
        data["preferred_trip_length_days"] = (
            None if value in (None, "") else require_int(payload, "preferred_trip_length_days", minimum=1)
        )
    minimum = data.get("budget_min")
    maximum = data.get("budget_max")
    if minimum is not None and maximum is not None and maximum < minimum:
        raise ValidationError("budget_max must be greater than or equal to budget_min")
    return data


def validate_interest(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not partial or "traveler_id" in payload:
        data["traveler_id"] = require_int(payload, "traveler_id", minimum=1)
    if not partial or "interest_category" in payload:
        data["interest_category"] = require_choice(
            payload, "interest_category", INTEREST_CATEGORIES
        )
    if not partial or "priority" in payload:
        if "priority" not in payload:
            data["priority"] = "medium"
        else:
            data["priority"] = require_choice(payload, "priority", PRIORITIES)
    return data


def validate_accessibility_need(payload: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not partial or "traveler_id" in payload:
        data["traveler_id"] = require_int(payload, "traveler_id", minimum=1)
    if not partial or "requirement" in payload:
        data["requirement"] = require_choice(
            payload, "requirement", ACCESSIBILITY_REQUIREMENTS
        )
    if not partial or "dietary_restriction" in payload:
        data["dietary_restriction"] = require_choice(
            payload, "dietary_restriction", DIETARY_RESTRICTIONS
        )
    if "notes" in payload:
        notes = payload["notes"]
        if notes is None or (isinstance(notes, str) and not notes.strip()):
            data["notes"] = None
        elif not isinstance(notes, str):
            raise ValidationError("notes must be a string")
        else:
            data["notes"] = notes.strip()
    return data
