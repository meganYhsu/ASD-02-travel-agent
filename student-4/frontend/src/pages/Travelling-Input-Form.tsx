import React, {useState} from 'react';
import {useLocation , useNavigate} from "react-router-dom";

function TravellingInputForm(){
    const userName = useState("");
    const [destination , setDestination] = useState("");
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const [budget, setBudget] = useState("");
    const [travelGroup, setTravelGroup] = useState("");
    const [travelStyle, setTravelStyle] = useState("");
    const [Requirements, setRequirements] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const location = useLocation()
    const navigation = useNavigate()



    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>)=> {
        event.preventDefault();
        setError("");
        if (travelStyle.length === 0) {
            setError("Please select at least one travel style.");
            return;
        }
        if(new Date(endDate)< new Date(startDate)){
            setError("the endDate can't be before startDate");
        }
        const travelPreference = {
            destination ,
            startDate,
            endDate,
            budget,
            travelGroup,
            travelStyle,
            Requirements,
        }

    //     if all the necessary values are provided then we can go ahead and send a request to the backend

        try{
            setLoading(true);
            const req = await fetch(
                "http://localhost:5001/api/cities",
                {
                    method:"POST",
                    headers:{
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(travelPreference)
                }
            );

            const resp = await req.json();

            if (!req.ok) {
                throw new Error(
                    resp.message || "Can't go further."
                );
            }
            console.log("Generated itineraries:", resp);
            navigation("/SelectCitiesPage", {
                state: {
                    cities: resp.cities,
                    destination:destination,
                    startDate:startDate,
                    endDate:endDate,
                    budget:budget,
                    travelPreference:travelPreference,
                    travelStyle:travelStyle
                }
            });
        }catch(e){
            if(e instanceof Error){
                setError(e.message|| "Couldn't send through your request");
            }

        }
        finally {
            setLoading(false);
        }
    }



//     a function to send API requests to backend and recieve wanted result.

    return (
        <div className="travel-page travel-page--form">
            <div className="travel-page__shell">
                <header className="travel-page__hero">
                    <p className="travel-page__eyebrow">Trip planner</p>
                    <h1 className="travel-page__title">Travelling style and destination</h1>
                    <p className="travel-page__intro">
                        Start with the basics and we will turn them into a more structured trip plan.
                    </p>
                </header>

                <div className="travel-panel">
                    <form className="travel-form" onSubmit={handleSubmit}>
                        {error && <p className="travel-form__error">{error}</p>}
                        <div className="travel-form__grid">
                            <label className="travel-form__field">
                                <span>Destination</span>
                                <input
                                    id="destination"
                                    name="destination"
                                    type="text"
                                    value={destination}
                                    onChange={(event) => setDestination(event.target.value)}
                                    placeholder="For example, Japan"
                                    required
                                />
                            </label>
                            <label className="travel-form__field">
                                <span>Budget</span>
                                <input
                                    type="text"
                                    id="budget"
                                    name="Budget"
                                    value={budget}
                                    onChange={(event) => setBudget(event.target.value)}
                                    placeholder="For example, AUD 4000"
                                    required
                                />
                            </label>
                            <label className="travel-form__field">
                                <span>Start Date</span>
                                <input
                                    id="startDate"
                                    name="startDate"
                                    type="date"
                                    value={startDate}
                                    onChange={(event) => setStartDate(event.target.value)}
                                    required
                                />
                            </label>
                            <label className="travel-form__field">
                                <span>End Date</span>
                                <input
                                    id="endDate"
                                    name="endDate"
                                    type="date"
                                    value={endDate}
                                    min={startDate}
                                    onChange={(event) => setEndDate(event.target.value)}
                                    required
                                />
                            </label>
                            <label className="travel-form__field">
                                <span>Travel group</span>
                                <select
                                    name="travelGroup"
                                    id="travelGroup"
                                    value={travelGroup}
                                    onChange={(event) => setTravelGroup(event.target.value)}
                                >
                                    <option value="">Select a travel group</option>
                                    <option value="solo">Solo</option>
                                    <option value="friends">Friends</option>
                                    <option value="family">Family</option>
                                    <option value="family-and-friends">Family and friends</option>
                                    <option value="large-group">Large group</option>
                                </select>
                            </label>
                            <label className="travel-form__field">
                                <span>Travel style</span>
                                <select
                                    id="travelStyle"
                                    name="travelStyle"
                                    value={travelStyle}
                                    onChange={(event) => setTravelStyle(event.target.value)}
                                    required
                                >
                                    <option value="">Select a travel style</option>
                                    <option value="Luxury Travel">Luxury Travel</option>
                                    <option value="Leisure Travel">Leisure Travel</option>
                                    <option value="Fast-Paced Travel">Fast-Paced Travel</option>
                                    <option value="Adventure Travel">Adventure Travel</option>
                                    <option value="Sightseeing Travel">Sightseeing Travel</option>
                                    <option value="Cultural Travel">Cultural Travel</option>
                                    <option value="Road Trip">Road Trip</option>
                                    <option value="Slow Travel">Slow Travel</option>
                                    <option value="Pilgrimage / Religious Travel">Pilgrimage / Religious Travel</option>
                                    <option value="Wellness Travel">Wellness Travel</option>
                                    <option value="Digital Nomad Travel">Digital Nomad Travel</option>
                                </select>
                            </label>
                        </div>

                        <button className="travel-button" type="submit" disabled={loading}>
                            {loading ? "Planning..." : "Continue"}
                        </button>
                    </form>
                </div>
            </div>
        </div>
    )
}

export default TravellingInputForm
