import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

type SavedActivity = {
    activity_id: number;
    itinerary_id: number;
    day_no: number;
    date: string;
    location: string;
    time: string;
    cost: string | null;
    note: string | null;
};

type SavedItinerary = {
    itinerary_id: number;
    destination: string;
    start_date: string;
    end_date: string;
    budget: string;
    travel_group: string | null;
    travel_style: string;
    requirements: string | null;
    created_at?: string;
};

type SavedItineraryPayload = {
    itinerary: SavedItinerary | null;
    activities: SavedActivity[];
};

function SavedItineraryPage() {
    const { id } = useParams();
    const location = useLocation();
    const navigate = useNavigate();
    const [data, setData] = useState<SavedItineraryPayload | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [deleting, setDeleting] = useState(false);

    const savedItineraryId = Number(id || (location.state as any)?.savedItineraryId || "");

    async function loadSavedItinerary() {
        if (!Number.isInteger(savedItineraryId)) {
            setError("Invalid itinerary id");
            return;
        }

        try {
            setLoading(true);
            setError("");

            const res = await fetch(`http://localhost:5001/api/saved_itineraries/${savedItineraryId}`);
            const payload = await res.json();

            if (!res.ok) {
                throw new Error(payload?.error || "Failed to load itinerary");
            }

            setData(payload);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to load itinerary";
            setError(message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        loadSavedItinerary();
    }, [savedItineraryId]);

    const activitiesByDay = useMemo(() => {
        const grouped = new Map<number, SavedActivity[]>();
        for (const activity of data?.activities || []) {
            const day = activity.day_no || 0;
            const current = grouped.get(day) || [];
            current.push(activity);
            grouped.set(day, current);
        }
        return Array.from(grouped.entries()).sort((a, b) => a[0] - b[0]);
    }, [data]);

    async function handleDelete() {
        if (!Number.isInteger(savedItineraryId)) {
            return;
        }

        try {
            setDeleting(true);
            const res = await fetch(`http://localhost:5001/api/saved_itineraries/${savedItineraryId}`, {
                method: "DELETE"
            });
            const payload = await res.json();

            if (!res.ok) {
                throw new Error(payload?.error || "Failed to delete itinerary");
            }

            navigate("/", {
                replace: true,
                state: {
                    deletedItineraryId: payload.deletedItineraryId
                }
            });
        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to delete itinerary";
            setError(message);
        } finally {
            setDeleting(false);
        }
    }

    const itinerary = data?.itinerary;

    return (
        <div className="saved-itinerary-page">
            <div className="saved-itinerary-page__shell">
                <header className="saved-itinerary-page__hero">
                    <p className="saved-itinerary-page__eyebrow">Saved itinerary</p>
                    <h1 className="saved-itinerary-page__title">
                        {itinerary?.destination || "Saved itinerary"}
                    </h1>
                    <p className="saved-itinerary-page__intro">
                        Review the itinerary that was stored in the backend and delete it if you want to start over.
                    </p>
                </header>

                {loading && <div className="saved-itinerary-page__state">Loading itinerary...</div>}
                {error && <div className="saved-itinerary-page__state saved-itinerary-page__state--error">{error}</div>}

                {!loading && itinerary && (
                    <>
                        <section className="saved-itinerary-page__summary">
                            <div className="saved-itinerary-page__card">
                                <span className="saved-itinerary-page__label">Dates</span>
                                <strong>{itinerary.start_date} to {itinerary.end_date}</strong>
                            </div>
                            <div className="saved-itinerary-page__card">
                                <span className="saved-itinerary-page__label">Budget</span>
                                <strong>{itinerary.budget}</strong>
                            </div>
                            <div className="saved-itinerary-page__card">
                                <span className="saved-itinerary-page__label">Group</span>
                                <strong>{itinerary.travel_group || "Not set"}</strong>
                            </div>
                            <div className="saved-itinerary-page__card">
                                <span className="saved-itinerary-page__label">Style</span>
                                <strong>{itinerary.travel_style}</strong>
                            </div>
                        </section>

                        <section className="saved-itinerary-page__panel">
                            <div className="saved-itinerary-page__section-head">
                                <div>
                                    <p className="saved-itinerary-page__eyebrow">Details</p>
                                    <h2 className="saved-itinerary-page__section-title">Itinerary and activities</h2>
                                </div>
                                <div className="saved-itinerary-page__meta">
                                    ID {itinerary.itinerary_id}
                                </div>
                            </div>

                            <p className="saved-itinerary-page__copy">
                                {itinerary.requirements || "No extra requirements were saved for this itinerary."}
                            </p>

                            <div className="saved-itinerary-page__activities">
                                {activitiesByDay.map(([dayNo, activities]) => (
                                    <article className="saved-itinerary-page__day" key={dayNo}>
                                        <div className="saved-itinerary-page__day-head">
                                            <div>
                                                <h3>Day {dayNo}</h3>
                                            </div>
                                            <div className="saved-itinerary-page__day-meta">
                                                <span>{activities[0]?.date}</span>
                                                <span>{activities[0]?.location}</span>
                                            </div>
                                        </div>
                                        <div className="saved-itinerary-page__activity-list">
                                            {activities.map((activity) => (
                                                <div className="saved-itinerary-page__activity" key={activity.activity_id}>
                                                    <div className="saved-itinerary-page__activity-time">{activity.time}</div>
                                                    <div>
                                                        <p>{activity.note || "No note saved"}</p>
                                                        {activity.cost && <span>{activity.cost}</span>}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </section>

                        <section className="saved-itinerary-page__actions">
                            <button
                                className="saved-itinerary-page__button saved-itinerary-page__button--danger"
                                type="button"
                                onClick={handleDelete}
                                disabled={deleting}
                            >
                                {deleting ? "Deleting..." : "Delete itinerary"}
                            </button>
                            <button
                                className="saved-itinerary-page__button"
                                type="button"
                                onClick={() => navigate("/")}
                            >
                                Back to planner
                            </button>
                        </section>
                    </>
                )}
            </div>
        </div>
    );
}

export default SavedItineraryPage;
