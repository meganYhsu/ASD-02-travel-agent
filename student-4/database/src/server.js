const express = require("express");
const cors = require("cors");
const db = require("./database");

const app = express();
app.use(cors());
app.use(express.json());

app.get("/health", (req, res) => {
  res.json({
    ok: true
  });
});

app.post("/api/itineraries", (req, res) => {
  const {
    destination,
    startDate,
    endDate,
    budget,
    travelGroup,
    travelStyle,
    requirements
  } = req.body;

  if (!destination || !startDate || !endDate || !budget || !travelStyle) {
    return res.status(400).json({
      error: "Missing required itinerary details"
    });
  }

  const requirementsValue =
    typeof requirements === "string"
      ? requirements
      : requirements !== undefined
        ? JSON.stringify(requirements)
        : null;

  const result = db.prepare(`
    INSERT INTO itinerary (
      destination,
      start_date,
      end_date,
      budget,
      travel_group,
      travel_style,
      requirements
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(
    destination,
    startDate,
    endDate,
    budget,
    travelGroup ?? null,
    travelStyle,
    requirementsValue
  );

  res.status(201).json({ itineraryId: result.lastInsertRowid });
});

app.post("/api/itineraries/:id/activities", (req, res) => {
  const itineraryId = Number(req.params.id);
  const { dayNo, date, location, time, cost, note } = req.body;

  if (!Number.isInteger(itineraryId)) {
    return res.status(400).json({
      error: "Invalid itinerary id"
    });
  }

  if (!dayNo || !date || !location || !time) {
    return res.status(400).json({
      error: "Missing required activity details"
    });
  }

  const result = db.prepare(`
    INSERT INTO activity (
      itinerary_id, day_no, date, location, time, cost, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
  `).run(itineraryId, dayNo, date, location, time, cost, note);

  res.status(201).json({ activityId: result.lastInsertRowid });
});


app.get("/api/itineraries/:id", (req, res) => {
  const itineraryId = Number(req.params.id);

  if (!Number.isInteger(itineraryId)) {
    return res.status(400).json({
      error: "Invalid itinerary id"
    });
  }

  const itinerary = db.prepare(`
    SELECT * FROM itinerary WHERE itinerary_id = ?
  `).get(itineraryId);

  const activities = db.prepare(`
    SELECT * FROM activity WHERE itinerary_id = ? ORDER BY day_no
  `).all(itineraryId);

  res.json({ itinerary, activities });
});

app.delete("/api/itineraries/:id", (req, res) => {
  const itineraryId = Number(req.params.id);

  if (!Number.isInteger(itineraryId)) {
    return res.status(400).json({
      error: "Invalid itinerary id"
    });
  }

  const deleteActivities = db.prepare(`
    DELETE FROM activity WHERE itinerary_id = ?
  `);

  const deleteItinerary = db.prepare(`
    DELETE FROM itinerary WHERE itinerary_id = ?
  `);

  const existingItinerary = db.prepare(`
    SELECT itinerary_id FROM itinerary WHERE itinerary_id = ?
  `).get(itineraryId);

  if (!existingItinerary) {
    return res.status(404).json({
      error: "Itinerary not found"
    });
  }

  deleteActivities.run(itineraryId);
  deleteItinerary.run(itineraryId);

  return res.json({
    ok: true,
    deletedItineraryId: itineraryId
  });
});

app.listen(5002, () => {
  console.log("Database service running on port 5002");
});
