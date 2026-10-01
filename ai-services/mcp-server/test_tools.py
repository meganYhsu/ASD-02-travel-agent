from datetime import date

import pytest

from tools import ToolError, days_until_departure, packing_climate_tip, passport_validity_check


def test_days_until_departure_computes_relative_days():
    departure = date.today()
    result = days_until_departure({"departure_date": departure.isoformat()})
    assert result["days_until_departure"] == 0
    assert result["has_departed"] is False


def test_days_until_departure_requires_argument():
    with pytest.raises(ToolError):
        days_until_departure({})


def test_passport_validity_check_meets_minimum():
    result = passport_validity_check(
        {"expiry_date": "2027-01-01", "return_date": "2026-09-10", "minimum_validity_days": 90}
    )
    assert result["meets_minimum_validity"] is True
    assert result["is_expired_by_return"] is False


def test_passport_validity_check_fails_minimum():
    result = passport_validity_check(
        {"expiry_date": "2026-09-15", "return_date": "2026-09-10", "minimum_validity_days": 180}
    )
    assert result["meets_minimum_validity"] is False


def test_passport_validity_check_invalid_date_raises():
    with pytest.raises(ToolError):
        passport_validity_check({"expiry_date": "not-a-date", "return_date": "2026-09-10"})


def test_packing_climate_tip_known_climate():
    result = packing_climate_tip({"climate": "Rainy"})
    assert result["matched"] is True
    assert "waterproof" in result["tip"]


def test_packing_climate_tip_unknown_climate_returns_matched_false():
    result = packing_climate_tip({"climate": "volcanic"})
    assert result["matched"] is False
