import React, {useState} from 'react';

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



    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>)=> {
        event.preventDefault();
        setError("");
        if (travelStyle.length === 0) {
            setError("Please select at least one travel style.");
            return;
        }
        if(new Date(startDate)< new Date(endDate)){
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
        for(const values in travelPreference){
            if(!values){
                setError("Please provide necessary values," );
            }
        }

    //     if all the necessary values are provided then we can go ahead and send a request to the backend

        try{
            setLoading(true);
            const req = await fetch(
                "http://localhost:5001/api/itineraries/generate",
                {
                    method:"POST",
                    headers:{
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(travelPreference)
                }
            );

            const resp = await req.json();

            if (!resp.ok) {
                throw new Error(
                    resp.message || "Can't go further."
                );
            }
            console.log("Generated itineraries:", resp);
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
        <div>
            <div className="All_Headings">
                <h1>Travelling style and Destination</h1>
            </div>
            <div className="TravellingForm">
                <form onSubmit={handleSubmit}>
                    <label htmlFor="">Destination</label>
                    <input
                        id="destination"
                        name="destination"
                        type="text"
                        value={destination}
                        onChange={(event) => setDestination(event.target.value)}
                        placeholder="For example, Japan"
                        required
                    />
                    <label htmlFor="StartDate">Start Date</label>
                    <input
                        id="startDate"
                        name="startDate"
                        type="date"
                        value={startDate}
                        onChange={(event) =>
                            setStartDate(event.target.value)
                        }
                        required
                    />
                    <label htmlFor="EndDate">End Date</label>
                    <input
                        id="endDate"
                        name="endDate"
                        type="date"
                        value={endDate}
                        min={startDate}
                        onChange={(event) =>
                            setEndDate(event.target.value)
                        }
                        required
                    />
                    <label htmlFor="">Budget</label>
                    <input type="text"
                    id="budget"
                    name="Budget"
                    value={budget}
                    onChange={(event) => setBudget(event.target.value)}
                    required/>
                    <label htmlFor="">Group of people going with</label>
                    <option value="">Select a travel group</option>
                    <select name="travelGroup" id="travelGroup"
                            value={travelGroup}
                            onChange={(event) => setTravelGroup(event.target.value)}
                    >
                        <option value="solo">Solo</option>
                        <option value="friends">Friends</option>
                        <option value="family">Family</option>
                        <option value="family-and-friends">Family and friends</option>
                        <option value="large-group">Large group</option>

                    </select>
                    <label htmlFor="Travelling Style"></label>
                    <select
                        id="travelStyle"
                        name="travelStyle"
                        value={travelStyle}
                        onChange={(event) =>
                            setTravelStyle(event.target.value)
                        }
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
                    <button type="submit">Submit</button>
                </form>
            </div>

        </div>
    )
}

export default TravellingInputForm