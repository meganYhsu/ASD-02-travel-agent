const DATABASE_URL =
    process.env.DATABASE_BASE_URL ||
    "http://localhost:5002";

async function saveItinerary(itineraryData) {
    const response = await fetch(
        `${DATABASE_URL}/api/itineraries`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                destination: itineraryData.destination,
                startDate: itineraryData.startDate,
                endDate: itineraryData.endDate,
                budget: itineraryData.budget,
                travelGroup: itineraryData.travelGroup ?? itineraryData.group ?? null,
                travelStyle: itineraryData.travelStyle,
                requirements: itineraryData.requirements || ""
            })
        }
    );

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to save itinerary: ${error}`);
    }

    return response.json();
}

async function saveActivity(itineraryId, activity) {
    const response = await fetch(
        `${DATABASE_URL}/api/itineraries/${itineraryId}/activities`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                dayNo: activity.dayNo,
                date: activity.date,
                location: activity.location,
                time: activity.time,
                cost: activity.cost || "",
                note: activity.note || ""
            })
        }
    );

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to save activity: ${error}`);
    }

    return response.json();
}

async function getItinerary(itineraryId) {
    const response = await fetch(`${DATABASE_URL}/api/itineraries/${itineraryId}`);

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to load itinerary: ${error}`);
    }

    return response.json();
}

async function deleteItinerary(itineraryId) {
    const response = await fetch(`${DATABASE_URL}/api/itineraries/${itineraryId}`, {
        method: "DELETE"
    });

    if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to delete itinerary: ${error}`);
    }

    return response.json();
}

module.exports = {
    saveItinerary,
    saveActivity,
    getItinerary,
    deleteItinerary
};
