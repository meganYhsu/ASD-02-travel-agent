import React, {useEffect, useState} from "react";
import {useLocation, useNavigate} from "react-router-dom";
// import "itinerary_Page.css";


function ItineraryPage(){
    // will be storing the complete itinerary here.
    // making a list of all the important and required data:
    const location = useLocation();
    const navigate = useNavigate();
    const [loading , setLoading] = useState(false);
    const [refinePrompt, setRefinePrompt] = useState("");
    const [saving, setSaving] = useState(false);
    const [saveMessage, setSaveMessage] = useState("");
    const [saveError, setSaveError] = useState("");
    const [savedItineraryId, setSavedItineraryId] = useState<number | null>(null);
    const {
        destination , startDate , endDate , cities , budget , group , travelStyle , travelPreference, c , selectedItinerary
    } = location.state || {};
    const [itinerary , setItinerary] = useState<any>(null);
    const itineraryCurrency = itinerary?.currency || "AUD";
    const tripCities = Array.isArray(cities) ? cities : [];
    const dayCount = Array.isArray(itinerary?.days) ? itinerary.days.length : 0;
    const activityCount = Array.isArray(itinerary?.days)
        ? itinerary.days.reduce((total: number, day: any) => total + (Array.isArray(day.activities) ? day.activities.length : 0), 0)
        : 0;
    const restaurantCount = Array.isArray(itinerary?.days)
        ? itinerary.days.reduce((total: number, day: any) => total + (Array.isArray(day.restaurants) ? day.restaurants.length : 0), 0)
        : 0;
    // making a react function that will help to send request and get a response.
    async function getitinerary(prompt = ""){
        // making a list of all the values and sending it to the backend so that
        // using api, groq will be able to get the complete itinerary:
        const UserTravelValues = {
            destination , startDate , endDate , cities , budget , group , travelStyle , travelPreference , c , selectedItinerary,
            improvementPrompt: prompt
        }
        try{
            setLoading(true);
            const res = await fetch("http://localhost:5001/api/generate_complete_selected_itinerary" ,
                {
                    method:"POST",
                    headers:{
                        "Content-Type":"application/json",
                    },
                    body:JSON.stringify(UserTravelValues)
                });
            const data = await res.json();

            let parsedData;
            if (typeof data.message === "string") {
                parsedData = JSON.parse(data.message);
            } else if (data.message && typeof data.message === "object") {
                parsedData = data.message;
            } else {
                parsedData = data;
            }

            setItinerary(parsedData);

        }
        catch (error) {
            console.error("Error generating itineraries:", error);
        }
        finally{
            setLoading(false);
        }


    }

    function handleImproveItinerary(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        updateItineraryFromPrompt(refinePrompt);
    }

    async function updateItineraryFromPrompt(prompt: string) {
        if (!itinerary) {
            return;
        }

        try {
            setLoading(true);
            const res = await fetch("http://localhost:5001/api/update_itinerary_from_prompt", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    improvementPrompt: prompt,
                    currentItinerary: itinerary,
                    destination,
                    startDate,
                    endDate,
                    cities,
                    budget,
                    group,
                    travelStyle,
                    travelPreference,
                    c,
                    selectedItinerary
                })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.error || "Failed to update itinerary");
            }

            setItinerary(data);
            setSavedItineraryId(null);
            setSaveMessage("");
            setSaveError("");
        } catch (error) {
            console.error("Error updating itinerary:", error);
        } finally {
            setLoading(false);
        }
    }

    async function saveCurrentItinerary() {
        if (!itinerary) {
            return;
        }

        try {
            setSaving(true);
            setSaveError("");
            setSaveMessage("");

            const res = await fetch("http://localhost:5001/api/save_itinerary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    currentItinerary: itinerary,
                    destination,
                    startDate,
                    endDate,
                    budget,
                    group,
                    travelStyle,
                    travelPreference,
                    c,
                    selectedItinerary
                })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data?.error || "Failed to save itinerary");
            }

            setSavedItineraryId(data?.itineraryId ?? null);
            setSaveMessage(
                data?.itineraryId
                    ? `Saved to the database as itinerary ${data.itineraryId}.`
                    : "Saved to the database."
            );
            if (data?.itineraryId) {
                navigate(`/saved-itinerary/${data.itineraryId}`, {
                    state: {
                        savedItineraryId: data.itineraryId
                    }
                });
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : "Failed to save itinerary";
            setSaveError(message);
        } finally {
            setSaving(false);
        }
    }

    useEffect(() => {
        getitinerary();
    }, []);

    useEffect(() => {
        setSaveMessage("");
        setSaveError("");
        setSavedItineraryId(null);
    }, [itinerary]);


    return(
        <div className="itinerary-page">
            <div className="itinerary-page__backdrop" />
            <div className="itinerary-page__shell">
                <header className="itinerary-page__hero">
                    <div className="itinerary-page__eyebrow">Norwegian-inspired travel planner</div>
                    <h1 className="itinerary-page__title">
                        {itinerary?.title || "Your Nordic itinerary is being prepared"}
                    </h1>
                    <p className="itinerary-page__intro">
                        A calm, fjord-toned travel brief for your trip to {destination || "your destination"}.
                        Once generated, you can refine it for slower mornings, better food stops, or a more scenic pace.
                    </p>

                    <div className="itinerary-page__meta-grid">
                        <div className="itinerary-page__meta-card">
                            <span className="itinerary-page__meta-label">Dates</span>
                            <strong>{startDate || "Start date"} to {endDate || "End date"}</strong>
                        </div>
                        <div className="itinerary-page__meta-card">
                            <span className="itinerary-page__meta-label">Budget</span>
                            <strong>{budget || "Budget not set"}</strong>
                        </div>
                        <div className="itinerary-page__meta-card">
                            <span className="itinerary-page__meta-label">Style</span>
                            <strong>{travelStyle || "Travel style"}</strong>
                        </div>
                        <div className="itinerary-page__meta-card">
                            <span className="itinerary-page__meta-label">Group</span>
                            <strong>{group || "Travel group"}</strong>
                        </div>
                    </div>
                </header>

                <section className="itinerary-page__refine-panel">
                    <div>
                        <p className="itinerary-page__section-label">Refine</p>
                        <h2 className="itinerary-page__section-title">Shape the route before you book it</h2>
                    </div>
                    <form className="itinerary-page__refine-form" onSubmit={handleImproveItinerary}>
                        <label className="itinerary-page__sr-only" htmlFor="refinePrompt">
                            Improve this itinerary
                        </label>
                        <input
                            id="refinePrompt"
                            className="itinerary-page__input"
                            type="text"
                            value={refinePrompt}
                            onChange={(event) => setRefinePrompt(event.target.value)}
                            placeholder="Add more seafood stops, make the days lighter, and keep the ferry rides scenic."
                        />
                        <button
                            className="itinerary-page__button"
                            type="submit"
                            disabled={loading || !itinerary}
                        >
                            {loading ? "Updating..." : "Refine itinerary"}
                        </button>
                    </form>
                </section>

                <section className="itinerary-page__content">
                    {loading && !itinerary && (
                        <div className="itinerary-page__state">
                            Building a cleaner, more detailed itinerary for your trip.
                        </div>
                    )}

                    {!loading && !itinerary && (
                        <div className="itinerary-page__state">
                            No itinerary found yet. Generate one from the previous step to see the full trip plan here.
                        </div>
                    )}

                    {!loading && itinerary && (
                        <div className="itinerary-page__itinerary">
                            <div className="itinerary-page__summary">
                                <div>
                                    <p className="itinerary-page__section-label">Overview</p>
                                    <p className="itinerary-page__summary-text">{itinerary.summary}</p>
                                </div>
                                <div className="itinerary-page__cost-card">
                                    <span className="itinerary-page__meta-label">Estimated cost</span>
                                    <strong>{itineraryCurrency} {itinerary.estimatedCost}</strong>
                                </div>
                            </div>

                            <div className="itinerary-page__facts">
                                <div className="itinerary-page__fact">
                                    <span className="itinerary-page__meta-label">Cities</span>
                                    <strong>{tripCities.length > 0 ? tripCities.join(", ") : destination || "Planned route"}</strong>
                                </div>
                                <div className="itinerary-page__fact">
                                    <span className="itinerary-page__meta-label">Days</span>
                                    <strong>{dayCount}</strong>
                                </div>
                                <div className="itinerary-page__fact">
                                    <span className="itinerary-page__meta-label">Activities</span>
                                    <strong>{activityCount}</strong>
                                </div>
                                <div className="itinerary-page__fact">
                                    <span className="itinerary-page__meta-label">Dining stops</span>
                                    <strong>{restaurantCount}</strong>
                                </div>
                            </div>

                            <div className="itinerary-page__timeline">
                                {itinerary.days?.map((day: any, index: number) => (
                                    <article className="itinerary-page__day" key={index}>
                                        <div className="itinerary-page__day-head">
                                            <div>
                                                <p className="itinerary-page__day-label">Day {day.dayNumber}</p>
                                                <h3 className="itinerary-page__day-title">{day.title}</h3>
                                            </div>
                                            <div className="itinerary-page__day-meta">
                                                <span>{day.date}</span>
                                                <span>{day.city}</span>
                                            </div>
                                        </div>

                                        <div className="itinerary-page__day-body">
                                            {day.activities?.map((activity: any, i: number) => (
                                                <div className="itinerary-page__activity" key={i}>
                                                    <div className="itinerary-page__activity-time">{activity.time}</div>
                                                    <div>
                                                        <h4 className="itinerary-page__activity-title">{activity.name}</h4>
                                                        <p className="itinerary-page__activity-copy">{activity.description}</p>
                                                    </div>
                                                </div>
                                            ))}

                                            {Array.isArray(day.restaurants) && day.restaurants.length > 0 && (
                                                <div className="itinerary-page__restaurants">
                                                    <h4 className="itinerary-page__subhead">Restaurants</h4>
                                                    <div className="itinerary-page__restaurant-grid">
                                                        {day.restaurants.map((restaurant: any, restaurantIndex: number) => (
                                                            <div className="itinerary-page__restaurant" key={restaurantIndex}>
                                                                <p className="itinerary-page__restaurant-meal">{restaurant.meal}</p>
                                                                <strong className="itinerary-page__restaurant-name">{restaurant.name}</strong>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </article>
                                ))}
                            </div>

                            <div className="itinerary-page__save-panel">
                                <div>
                                    <p className="itinerary-page__section-label">Save</p>

                                </div>
                                <div className="itinerary-page__save-actions">
                                    <button
                                        className="itinerary-page__button"
                                        type="button"
                                        onClick={saveCurrentItinerary}
                                        disabled={loading || saving || !itinerary || savedItineraryId !== null}
                                    >
                                        {saving ? "Saving..." : savedItineraryId !== null ? "Saved" : "Save itinerary"}
                                    </button>
                                    {saveMessage && (
                                        <p className="itinerary-page__save-status">{saveMessage}</p>
                                    )}
                                    {saveError && (
                                        <p className="itinerary-page__save-status itinerary-page__save-status--error">
                                            {saveError}
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </section>
            </div>
        </div>
    )

}

export default ItineraryPage;
