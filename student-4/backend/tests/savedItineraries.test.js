const assert = require("node:assert/strict");
const { once } = require("node:events");
const { after, before, beforeEach, test } = require("node:test");
const express = require("express");

const itinerary = {
    itinerary_id: 42,
    destination: "Sydney",
    start_date: "2026-11-01",
    end_date: "2026-11-02",
    budget: "500"
};
const activities = [{
    activity_id: 1,
    itinerary_id: 42,
    day_no: 1,
    location: "Sydney Opera House",
    time: "10:00",
    note: "Guided tour"
}];

let databaseServer;
let backendServer;
let backendUrl;
let databaseResponse;
let databaseRequests;
const originalDatabaseUrl = process.env.DATABASE_BASE_URL;

before(async () => {
    const databaseApp = express();
    databaseApp.use((req, res) => {
        databaseRequests.push({ method: req.method, path: req.originalUrl });
        res.status(databaseResponse.status).json(databaseResponse.body);
    });
    databaseServer = databaseApp.listen(0, "127.0.0.1");
    await once(databaseServer, "listening");
    process.env.DATABASE_BASE_URL = `http://127.0.0.1:${databaseServer.address().port}`;

    const backendApp = express();
    backendApp.use("/api", require("../src/routes/getItineraryRoute"));
    backendServer = backendApp.listen(0, "127.0.0.1");
    await once(backendServer, "listening");
    backendUrl = `http://127.0.0.1:${backendServer.address().port}`;
});

beforeEach(() => {
    databaseRequests = [];
    databaseResponse = { status: 200, body: [] };
});

after(async () => {
    for (const server of [backendServer, databaseServer]) {
        if (server?.listening) {
            server.closeAllConnections();
            await new Promise((resolve, reject) => {
                server.close(error => error ? reject(error) : resolve());
            });
        }
    }
    if (originalDatabaseUrl === undefined) {
        delete process.env.DATABASE_BASE_URL;
    } else {
        process.env.DATABASE_BASE_URL = originalDatabaseUrl;
    }
});

test("GET /api/saved_itineraries returns saved itinerary contents", async () => {
    databaseResponse.body = [itinerary];

    const response = await fetch(`${backendUrl}/api/saved_itineraries`);

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), [itinerary]);
    assert.deepEqual(databaseRequests, [{ method: "GET", path: "/api/itineraries" }]);
});

test("GET /api/saved_itineraries returns an empty list when none are saved", async () => {
    const response = await fetch(`${backendUrl}/api/saved_itineraries`);

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), []);
});

test("GET /api/saved_itineraries handles database errors without leaking details", async () => {
    databaseResponse = { status: 500, body: { error: "Private database details" } };

    const response = await fetch(`${backendUrl}/api/saved_itineraries`);

    assert.equal(response.status, 500);
    assert.deepEqual(await response.json(), { error: "Could not get saved itineraries" });
});

test("GET /api/saved_itineraries/:id returns the itinerary and activities", async () => {
    databaseResponse.body = { itinerary, activities };

    const response = await fetch(`${backendUrl}/api/saved_itineraries/42`);

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { itinerary, activities });
    assert.deepEqual(databaseRequests, [{ method: "GET", path: "/api/itineraries/42" }]);
});

test("GET /api/saved_itineraries/:id rejects an invalid ID before calling the database", async () => {
    const response = await fetch(`${backendUrl}/api/saved_itineraries/not-an-id`);

    assert.equal(response.status, 400);
    assert.deepEqual(await response.json(), { error: "Invalid itinerary id" });
    assert.deepEqual(databaseRequests, []);
});

test("GET /api/saved_itineraries/:id returns 404 when the database reports a missing ID", async () => {
    databaseResponse = { status: 404, body: { error: "Itinerary not found" } };

    const response = await fetch(`${backendUrl}/api/saved_itineraries/999`);

    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: "Itinerary not found" });
    assert.deepEqual(databaseRequests, [{ method: "GET", path: "/api/itineraries/999" }]);
});

test("GET /api/saved_itineraries/:id returns 404 for an empty database result", async () => {
    databaseResponse.body = null;

    const response = await fetch(`${backendUrl}/api/saved_itineraries/999`);

    assert.equal(response.status, 404);
    assert.deepEqual(await response.json(), { error: "Itinerary not found" });
});

test("GET /api/saved_itineraries/:id handles database errors without leaking details", async () => {
    databaseResponse = { status: 500, body: { error: "Private database details" } };

    const response = await fetch(`${backendUrl}/api/saved_itineraries/42`);

    assert.equal(response.status, 500);
    assert.deepEqual(await response.json(), { error: "Could not load itinerary" });
});
