import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

type ItineraryDay = {
    dayNumber: number;
    date: string;
    city: string;
    title: string;
    overview: string;
};

type ItineraryOption = {
    id: number;
    title: string;
    type: string;
    summary: string;
    estimatedCost: number;
    currency: string;
    highlights: string[];
    days: ItineraryDay[];
};

function ItineraryOptions() {
    const location = useLocation();
    const navigate = useNavigate();
    const {
        destination,
        startDate,
        endDate,
        cities,
        budget,
        group,
        travelStyle,
        travelPreference,
        c
    } = location.state || {};

    const [itineraries, setItineraries] = useState<ItineraryOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function generateItineraries() {
        const details = {
            destination,
            startDate,
            endDate,
            cities,
            budget,
            group,
            travelStyle,
            travelPreference,
            c
        };

        try {
            setLoading(true);
            setError("");

            const res = await fetch("http://localhost:5001/api/request_itineraries", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(details)
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.error || "Failed to load itinerary options");
            }

            const options = Array.isArray(data?.itineraries)
                ? data.itineraries
                : Array.isArray(data)
                    ? data
                    : [];

            setItineraries(options);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to load itinerary options";
            setError(message);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        generateItineraries();
    }, []);

    function handleSelectItinerary(option: ItineraryOption) {
        navigate("/ItineraryPage", {
            state: {
                destination,
                startDate,
                endDate,
                cities,
                budget,
                group,
                travelStyle,
                travelPreference,
                c,
                selectedItinerary: option
            }
        });
    }

    return (
        <div className="travel-page travel-page--options">
            <div className="travel-page__shell">
                <header className="travel-page__hero">
                    <p className="travel-page__eyebrow">Trip planner</p>
                    <h1 className="travel-page__title">Itinerary options</h1>
                    <p className="travel-page__intro">
                        Compare two trip styles before you commit to one.
                    </p>
                </header>

                {loading && <div className="travel-panel travel-state">Loading itinerary options...</div>}
                {error && <div className="travel-panel travel-state travel-state--error">{error}</div>}

                <div className="option-grid">
                    {itineraries.map((option) => (
                        <article className="option-card" key={option.id}>
                            <div className="option-card__head">
                                <div>
                                    <p className="travel-page__eyebrow">Option {option.id}</p>
                                    <h2 className="option-card__title">{option.title}</h2>
                                </div>
                                <span className="option-card__tag">{option.type}</span>
                            </div>

                            <p className="option-card__summary">{option.summary}</p>

                            <div className="option-card__cost">
                                {option.currency} {option.estimatedCost}
                            </div>

                            <div className="option-card__section">
                                <h3 className="option-card__label">Highlights</h3>
                                <ul className="option-card__list">
                                    {option.highlights?.map((highlight, index) => (
                                        <li key={index}>{highlight}</li>
                                    ))}
                                </ul>
                            </div>

                            <div className="option-card__section">
                                <h3 className="option-card__label">Day by day</h3>
                                <div className="option-card__days">
                                    {option.days?.map((day) => (
                                        <div className="option-day" key={day.dayNumber}>
                                            <strong>Day {day.dayNumber}</strong>
                                            <div className="option-day__meta">
                                                {day.date} | {day.city}
                                            </div>
                                            <div className="option-day__title">{day.title}</div>
                                            <p>{day.overview}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <button
                                className="travel-button"
                                type="button"
                                onClick={() => handleSelectItinerary(option)}
                            >
                                Choose this itinerary
                            </button>
                        </article>
                    ))}
                </div>

                {!loading && !error && itineraries.length === 0 && (
                    <div className="travel-panel travel-state">
                        No itinerary options returned yet.
                    </div>
                )}
            </div>
        </div>
    );
}

export default ItineraryOptions;
