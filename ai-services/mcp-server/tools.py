import json
import os
import urllib.error
import urllib.request


DATABASE_BASE_URL = os.environ.get(
    "STUDENT4_DATABASE_BASE_URL",
    "http://localhost:6004"
).rstrip("/")


class DatabaseRequestError(Exception):
    pass


def _get_itinerary_payload(itinerary_id):
    url = f"{DATABASE_BASE_URL}/api/itineraries/{itinerary_id}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        raise DatabaseRequestError(
            f"Database request failed: {error.code} {body}"
        ) from error
    except urllib.error.URLError as error:
        raise DatabaseRequestError(
            f"Unable to connect to database service: {error.reason}"
        ) from error


def _get_itinerary_and_activities(itinerary_id):
    payload = _get_itinerary_payload(itinerary_id)
    itinerary = payload.get("itinerary")
    activities = payload.get("activities") or []

    if not itinerary:
        return None, activities

    return itinerary, activities


def total_activity_count(itinerary_id):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "error": "Itinerary not found",
            "total_no_of_activities": 0
        }

    return {
        "itinerary_id": itinerary_id,
        "total_no_of_activities": len(activities)
    }


def total_activities_count_a_day(itinerary_id, day_no):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "day_no": day_no,
            "error": "Itinerary not found",
            "total_no_of_activities_on_that_day": 0
        }

    total = sum(
        1 for activity in activities
        if activity.get("day_no") == day_no
    )

    return {
        "itinerary_id": itinerary_id,
        "day_no": day_no,
        "total_no_of_activities_on_that_day": total
    }


def get_trip_activities_desc(itinerary_id):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "error": "Itinerary not found",
            "activity_description": []
        }

    return {
        "activity_description": [
            activity.get("note")
            for activity in activities
            if activity.get("note")
        ]
    }


def get_trip_activities_for_day_desc(itinerary_id, day_no):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "day_no": day_no,
            "error": "Itinerary not found",
            "activity_description": []
        }

    return {
        "day_no": day_no,
        "activity_description": [
            activity.get("note")
            for activity in activities
            if activity.get("day_no") == day_no and activity.get("note")
        ]
    }


def get_activity_start_times(itinerary_id):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "error": "Itinerary not found",
            "activity_start_times": []
        }

    sorted_activities = sorted(
        activities,
        key=lambda activity: (
            activity.get("day_no") or 0,
            activity.get("time") or ""
        )
    )

    return {
        "itinerary_id": itinerary_id,
        "activity_start_times": [
            {
                "activity_description": activity.get("note"),
                "activity_start_time": activity.get("time")
            }
            for activity in sorted_activities
        ]
    }


def get_travel_requirements(itinerary_id):
    itinerary, activities = _get_itinerary_and_activities(itinerary_id)

    if itinerary is None:
        return {
            "itinerary_id": itinerary_id,
            "error": "Itinerary not found",
            "Requirements to travel": None
        }

    return {
        "Requirements to travel": itinerary.get("requirements")
    }


# ---------------------------------------------------------------- student 1
# Traveler Preferences tools. They read the Student 1 database API's
# preference-set contract, so the MCP server never touches preferences.db.

STUDENT1_DATABASE_BASE_URL = os.environ.get(
    "STUDENT1_DATABASE_BASE_URL",
    "http://localhost:6001"
).rstrip("/")


def _validate_traveler_id(traveler_id):
    # Tool boundary: only a positive whole-number traveler_id is accepted.
    if isinstance(traveler_id, bool) or not isinstance(traveler_id, int) or traveler_id < 1:
        raise ValueError("traveler_id must be a positive integer")


def _get_preference_set(traveler_id):
    _validate_traveler_id(traveler_id)
    url = f"{STUDENT1_DATABASE_BASE_URL}/preference-set/{traveler_id}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        body = error.read().decode("utf-8")
        raise DatabaseRequestError(
            f"Database request failed: {error.code} {body}"
        ) from error
    except urllib.error.URLError as error:
        raise DatabaseRequestError(
            f"Unable to connect to database service: {error.reason}"
        ) from error


def get_traveler_profile(traveler_id):
    profile = _get_preference_set(traveler_id)

    if profile is None:
        return {
            "traveler_id": traveler_id,
            "error": "Traveler not found"
        }

    traveler = profile["traveler"]
    preference = profile.get("preferences")

    return {
        "traveler_id": traveler_id,
        "name": traveler.get("name"),
        "home_location": traveler.get("home_location"),
        "travel_style": traveler.get("travel_style"),
        "budget": {
            "min": preference.get("budget_min"),
            "max": preference.get("budget_max"),
            "currency": preference.get("currency")
        } if preference else None,
        "pace": preference.get("pace") if preference else None
    }


def get_traveler_interests(traveler_id):
    profile = _get_preference_set(traveler_id)

    if profile is None:
        return {
            "traveler_id": traveler_id,
            "error": "Traveler not found",
            "interests": []
        }

    # The database API already orders interests by priority, highest first.
    return {
        "traveler_id": traveler_id,
        "interests": [
            {
                "interest_category": interest.get("interest_category"),
                "priority": interest.get("priority")
            }
            for interest in profile.get("interests") or []
        ]
    }


def get_accessibility_needs(traveler_id):
    profile = _get_preference_set(traveler_id)

    if profile is None:
        return {
            "traveler_id": traveler_id,
            "error": "Traveler not found",
            "accessibility_needs": []
        }

    return {
        "traveler_id": traveler_id,
        "accessibility_needs": [
            {
                "requirement": need.get("requirement"),
                "dietary_restriction": need.get("dietary_restriction")
            }
            for need in profile.get("accessibility_needs") or []
        ]
    }
