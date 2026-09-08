const DATABASE_URL =
    process.env.DATABASE_BASE_URL ||
    "http://localhost:5002";

class DatabaseUnavailableError extends Error {
    constructor(message = "Database service is unavailable") {
        super(message);
        this.name = "DatabaseUnavailableError";
    }
}

class DatabaseRequestError extends Error {
    constructor(status, message) {
        super(message);
        this.name = "DatabaseRequestError";
        this.status = status;
    }
}


async function request(method, path, body = null) {

    const controller = new AbortController();

    const timeout = setTimeout(() => {
        controller.abort();
    }, 10000);

    const options = {
        method,
        headers: {
            "Content-Type": "application/json"
        },
        signal: controller.signal
    };

    if (body !== null) {
        options.body = JSON.stringify(body);
    }

    try {

        const response = await fetch(
            `${DATABASE_URL}${path}`,
            options
        );

        if (!response.ok) {

            const error = await response.text();

            throw new DatabaseRequestError(
                response.status,
                `Database request failed: ${response.status} ${error}`
            );
        }

        return response.json();

    } catch (error) {

        // Database took longer than 10 seconds
        if (error.name === "AbortError") {
            throw new DatabaseUnavailableError(
                "Database request timed out after 10 seconds"
            );
        }

        // This is an HTTP error returned by the database itself.
        // Do not replace it with "database unavailable".
        if (error instanceof DatabaseRequestError) {
            throw error;
        }

        // Connection failed, database service is offline, bad hostname, etc.
        throw new DatabaseUnavailableError(
            `Unable to connect to database service: ${error.message}`
        );

    } finally {

        clearTimeout(timeout);
    }
}

async function saveItinerary(itineraryData) {

    return request(
        "POST",
        "/api/itineraries",
        {
            destination: itineraryData.destination,
            startDate: itineraryData.startDate,
            endDate: itineraryData.endDate,
            budget: itineraryData.budget,

            travelGroup:
                itineraryData.travelGroup ??
                itineraryData.group ??
                null,

            travelStyle: itineraryData.travelStyle,

            requirements:
                itineraryData.requirements || ""
        }
    );
}


async function saveActivity(itineraryId, activity) {

    return request(
        "POST",
        `/api/itineraries/${itineraryId}/activities`,
        {
            dayNo: activity.dayNo,
            date: activity.date,
            location: activity.location,
            time: activity.time,
            cost: activity.cost || "",
            note: activity.note || ""
        }
    );
}


async function getItinerary(itineraryId) {

    return request(
        "GET",
        `/api/itineraries/${itineraryId}`
    );
}


async function deleteItinerary(itineraryId) {

    return request(
        "DELETE",
        `/api/itineraries/${itineraryId}`
    );
}


module.exports = {
    saveItinerary,
    saveActivity,
    getItinerary,
    deleteItinerary,
    DatabaseUnavailableError,
    DatabaseRequestError
};