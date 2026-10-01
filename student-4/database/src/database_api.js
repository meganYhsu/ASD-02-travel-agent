//here, i wil be adding necesasry functions which needs to be called to make
// in the mco_mode.js file
// todo: this part is not complete yet.
//         it still needs some work and you have to add all the requried MCP functions here as well.

//connecting to the database:

const DATABASE_SERVICE_URL = process.env.DATABASE_SERVICE_URL || "http://database-service:5002";


//adding function to get data from the url.

async function getItinerary(itineraryID){
    const response = await fetch(`${DATABASE_SERVICE_URL}/api/itineraries/${itineraryId}`)

//     error handing:
    if(!response.ok){
        throw new Error('Failed to get itinerary:${response.status}')
    }

    const data = await response.json();
    return data.itinerary;
}

async function getActivitiesFromItinerary(itineraryID){
    const response = await fetch(
        `${DATABASE_SERVICE_URL}/api/itineraries/${itineraryId}`
    );

    if (!response.ok) {
        throw new Error(`Failed to get itinerary activities: ${response.status}`);
    }

    const data = await response.json();

    return data.activities;
}



