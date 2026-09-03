import os


def env(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATABASE_SERVICE_URL = env("DATABASE_SERVICE_URL", "http://127.0.0.1:5405")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_TIMEOUT_SECONDS = int(env("OLLAMA_TIMEOUT_SECONDS", "60"))
EXPIRY_WARNING_DAYS = int(env("EXPIRY_WARNING_DAYS", "90"))
PORT = int(env("PORT", "5505"))
DOCUMENT_TYPES = (
    "Passport",
    "Visa",
    "Travel Permit",
    "Vaccination Certificate",
    "Other",
)
REQUIREMENT_TYPES = (
    "Passport required",
    "Minimum passport validity",
    "Visa required",
    "Visa not required",
    "Vaccination required",
    "Travel permit required",
    "Other",
)
CATEGORIES = (
    "Clothing",
    "Toiletries",
    "Electronics",
    "Documents",
    "Medication / Health",
    "Activity Equipment",
    "Miscellaneous",
)
PRIORITIES = ("low", "medium", "high")
DOCUMENT_STATUSES = ("valid", "expiring", "expired", "revoked")
