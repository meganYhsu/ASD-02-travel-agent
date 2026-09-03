import os


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATABASE_SERVICE_URL = env("DATABASE_SERVICE_URL", "http://127.0.0.1:5402")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_SECONDS = int(env("OLLAMA_TIMEOUT_SECONDS", "120"))
PORT = int(env("PORT", "5502"))

# Minimum completeness score before Trip Planning (student-4) may consume a profile.
COMPLETENESS_THRESHOLD = int(env("COMPLETENESS_THRESHOLD", "75"))

TRAVEL_STYLES = ("Budget", "Mid-range", "Luxury")
PACES = ("relaxed", "balanced", "packed")
PRIORITIES = ("low", "medium", "high")
CURRENCIES = ("AUD", "NZD", "USD", "EUR", "GBP", "JPY")
INTEREST_CATEGORIES = (
    "Food & Dining",
    "History & Culture",
    "Nature & Outdoors",
    "Art & Museums",
    "Nightlife",
    "Shopping",
    "Adventure Sports",
    "Beaches",
    "Architecture",
    "Local Experiences",
    "Wellness & Spa",
    "Photography",
)
ACCESSIBILITY_REQUIREMENTS = (
    "None",
    "Step-free access",
    "Wheelchair accessible",
    "Limited walking",
    "Visual assistance",
    "Hearing assistance",
    "Service animal",
    "Accessible bathroom",
    "Elevator required",
    "Other",
)
DIETARY_RESTRICTIONS = (
    "None",
    "Vegetarian",
    "Vegan",
    "Halal",
    "Kosher",
    "Gluten-free",
    "Nut allergy",
    "Dairy-free",
    "Shellfish allergy",
    "Other",
)
