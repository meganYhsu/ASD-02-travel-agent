import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";


function SelectCitiesPage() {
    const location = useLocation();
    const navigation = useNavigate();

    // Get cities from previous page
    const { cities = [] } = location.state || {};

    // Store currently selected city
    const [selectedcity, setSelectedcity] = useState<string[]>([]);
    // Store cities typed in the textbox.
    const [cityInput, setCityInput] = useState<string>("");
    const [customCities, setCustomCities] = useState<string[]>([]);

    const allCities = Array.from(new Set([...cities, ...customCities]));

    function addCities(city:string){
        if(selectedcity.includes(city)){
            setSelectedcity(
                selectedcity.filter((cities:string) => cities !== city));

            

        }
        else{
            setSelectedcity([...selectedcity, city]);
        }
    }

    function addNewCity() {
        const newCity = cityInput.trim();
        if (!newCity) {
            return;
        }

        setCustomCities((prev) => {
            if (prev.includes(newCity) || cities.includes(newCity)) {
                return prev;
            }
            return [...prev, newCity];
        });
        setCityInput("");
    }

    return (
        <div className="travel-page travel-page--cities">
            <div className="travel-page__shell">
                <header className="travel-page__hero">
                    <p className="travel-page__eyebrow">Trip planner</p>
                    <h1 className="travel-page__title">Select cities</h1>
                    <p className="travel-page__intro">
                        Choose the places you want included in the route, or add your own stops.
                    </p>
                </header>

                <section className="travel-panel">
                    <div className="city-grid">
                        {allCities.map((city: string) => (
                            <label className="city-chip" key={city}>
                                <input
                                    type="checkbox"
                                    value={city}
                                    checked={selectedcity.includes(city)}
                                    onChange={() => addCities(city)}
                                />
                                <span>{city}</span>
                            </label>
                        ))}
                    </div>

                    <div className="travel-form__inline">
                        <input
                            className="travel-input"
                            type="text"
                            placeholder="Enter your preferred cities, separated by commas"
                            value={cityInput}
                            onChange={(e) => setCityInput(e.target.value)}
                        />
                        <button className="travel-button travel-button--secondary" type="button" onClick={addNewCity}>
                            Add city
                        </button>
                    </div>

                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => {
                            navigation("/ItineraryOptions", {
                                state: {
                                    destination: location.state.destination,
                                    startDate: location.state.startDate,
                                    endDate: location.state.endDate,
                                    budget: location.state.budget,
                                    travelPreference: location.state.travelPreference,
                                    travelStyle: location.state.travelStyle,
                                    c: selectedcity
                                }
                            });
                        }}
                    >
                        Continue
                    </button>
                </section>
            </div>
        </div>
    );
}

export default SelectCitiesPage;
