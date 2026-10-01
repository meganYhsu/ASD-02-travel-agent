from rag_pipeline import retrieve_context
from statistics import mean
from datetime import datetime


TEST_CASES = [
    {
        "name": "Student 1 - Traveller Preferences",
        "query": "What travel preferences or interests does the traveller have?",
        "relevant_sources": {
            "student1-preferences",
            "student1-interests",
        },
    },
    {
        "name": "Student 2 - Booking & Itinerary",
        "query": "What activities are planned or booked in Sydney?",
        "relevant_sources": {
            "student2-itineraries",
            "student2-bookings",
            "student2-booking_items",
        },
    },
    {
        "name": "Student 3 - Budget",
        "query": "What expenses or budget recommendations are recorded for the trip?",
        "relevant_sources": {
            "student3-expenses",
            "student3-recommendations",
        },
    },
    {
        "name": "Student 4 - Travel Plan",
        "query": "What activities are included in the Japan travel plan?",
        "relevant_sources": {
            "student4-travel-plans",
        },
    },
    {
        "name": "Student 5 - Pre-trip",
        "query": "What documents or pre-trip tasks are required for travel to Japan?",
        "relevant_sources": {
            "student5-documents",
            "student5-entry_requirements",
            "student5-pre_trip_tasks",
        },
    },
]


def evaluate_case(case, k=5):
    result = retrieve_context(case["query"], k=k)
    retrieved = result.get("results", [])

    relevant_hits = [
        item for item in retrieved
        if item.get("source_id") in case["relevant_sources"]
    ]

    precision = len(relevant_hits) / k if k else 0.0

    # For this project-level evaluation, Recall@K checks whether the
    # expected relevant source types were represented in Top-K.
    retrieved_sources = {
        item.get("source_id")
        for item in retrieved
    }

    expected_sources = case["relevant_sources"]

    matched_sources = retrieved_sources.intersection(expected_sources)

    recall = (
        len(matched_sources) / len(expected_sources)
        if expected_sources else 0.0
    )

    return {
        "name": case["name"],
        "query": case["query"],
        "precision_at_5": precision,
        "recall_at_5": recall,
        "retrieved": retrieved,
        "matched_sources": sorted(matched_sources),
    }


def main():
    results = []

    print("=" * 80)
    print("Shared RAG Retrieval Evaluation")
    print("=" * 80)

    for case in TEST_CASES:
        evaluation = evaluate_case(case)
        results.append(evaluation)

        print(f"\n{evaluation['name']}")
        print(f"Query: {evaluation['query']}")
        print(f"P@5: {evaluation['precision_at_5']:.2f}")
        print(f"R@5: {evaluation['recall_at_5']:.2f}")
        print(
            "Matched sources:",
            ", ".join(evaluation["matched_sources"]) or "None"
        )

        for item in evaluation["retrieved"]:
            print(
                f"  Rank {item.get('rank')} | "
                f"{item.get('chunk_id')} | "
                f"{item.get('source_id')}"
            )

    avg_precision = mean(
        item["precision_at_5"] for item in results
    )

    avg_recall = mean(
        item["recall_at_5"] for item in results
    )

    print("\n" + "=" * 80)
    print(f"Average P@5: {avg_precision:.2f}")
    print(f"Average R@5: {avg_recall:.2f}")
    print(f"Evaluated at: {datetime.now().isoformat(timespec='seconds')}")
    print("=" * 80)


if __name__ == "__main__":
    main()