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
