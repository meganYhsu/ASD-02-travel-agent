"""Deterministic profile-completeness scoring.

The AI layer explains and enriches these results, but never replaces them:
the score below is computed from stored records only, so it stays reproducible
and testable without a running LLM.
"""

from __future__ import annotations

from typing import Any

TRAVELER_CORE_FIELDS = ("full_name", "username", "email", "home_location", "travel_style")

WEIGHT_TRAVELER = 25
WEIGHT_PREFERENCES = 30
WEIGHT_INTERESTS = 25
WEIGHT_ACCESSIBILITY = 20

MIN_RECOMMENDED_INTERESTS = 3


def score_profile(profile: dict[str, Any], threshold: int) -> dict[str, Any]:
    """Return a completeness breakdown for an aggregated traveller profile."""
    traveler = profile.get("traveler") or {}
    preferences = profile.get("preferences")
    interests = profile.get("interests") or []
    accessibility = profile.get("accessibility_needs") or []

    missing: list[str] = []
    recommendations: list[str] = []
    score = 0

    missing_core = [
        field for field in TRAVELER_CORE_FIELDS
        if not str(traveler.get(field) or "").strip()
    ]
    if not missing_core:
        score += WEIGHT_TRAVELER
    else:
        missing.extend(f"traveler.{field}" for field in missing_core)
        recommendations.append(
            "Complete the traveller record: " + ", ".join(missing_core) + "."
        )

    if preferences:
        score += WEIGHT_PREFERENCES
    else:
        missing.append("preferences")
        recommendations.append(
            "Set a budget range and travel pace so itineraries can be costed."
        )

    if len(interests) >= MIN_RECOMMENDED_INTERESTS:
        score += WEIGHT_INTERESTS
    elif interests:
        score += WEIGHT_INTERESTS // 2
        recommendations.append(
            f"Add at least {MIN_RECOMMENDED_INTERESTS} interests "
            f"(currently {len(interests)}) to improve recommendation quality."
        )
    else:
        missing.append("interests")
        recommendations.append("Select at least one interest category.")

    if accessibility:
        score += WEIGHT_ACCESSIBILITY
    else:
        missing.append("accessibility_needs")
        recommendations.append(
            "Record accessibility and dietary needs, or explicitly select 'None'."
        )

    ready = bool(preferences) and bool(interests) and score >= threshold
    if ready and not recommendations:
        recommendations.append("Profile is ready for trip planning.")

    return {
        "traveler_id": traveler.get("id"),
        "score": score,
        "threshold": threshold,
        "is_complete": score == 100,
        "ready_for_trip_planning": ready,
        "missing": missing,
        "recommendations": recommendations,
        "counts": {
            "interests": len(interests),
            "accessibility_needs": len(accessibility),
            "has_preferences": bool(preferences),
        },
    }


def structured_preference_set(profile: dict[str, Any]) -> dict[str, Any]:
    """Flatten a profile into the contract other microservices consume."""
    traveler = profile.get("traveler") or {}
    preferences = profile.get("preferences") or {}
    interests = profile.get("interests") or []
    accessibility = profile.get("accessibility_needs") or []

    ranked = sorted(
        interests,
        key=lambda item: {"high": 0, "medium": 1, "low": 2}.get(item.get("priority"), 3),
    )
    return {
        "traveler_id": traveler.get("id"),
        "full_name": traveler.get("full_name"),
        "home_location": traveler.get("home_location"),
        "travel_style": traveler.get("travel_style"),
        "budget": {
            "min": preferences.get("budget_min"),
            "max": preferences.get("budget_max"),
            "currency": preferences.get("currency"),
        }
        if preferences
        else None,
        "pace": preferences.get("pace") if preferences else None,
        "preferred_trip_length_days": (
            preferences.get("preferred_trip_length_days") if preferences else None
        ),
        "interests": [item.get("interest_category") for item in ranked],
        "top_interests": [
            item.get("interest_category") for item in ranked if item.get("priority") == "high"
        ],
        "accessibility_requirements": sorted(
            {item.get("requirement") for item in accessibility if item.get("requirement") != "None"}
        ),
        "dietary_restrictions": sorted(
            {
                item.get("dietary_restriction")
                for item in accessibility
                if item.get("dietary_restriction") != "None"
            }
        ),
    }
