const express = require("express");
const router = express.Router();

const db = require("./database");

router.get("/itineraries/:id", (req, res) => {

    const itineraryId = Number(req.params.id);

    if (!Number.isInteger(itineraryId)) {
        return res.status(400).json({
            error: "Invalid itinerary id"
        });
    }

    try {

        const itinerary = db.prepare(`
            SELECT *
            FROM itinerary
            WHERE itinerary_id = ?
        `).get(itineraryId);

        if (!itinerary) {
            return res.status(404).json({
                error: "Itinerary not found"
            });
        }

        return res.status(200).json(itinerary);

    } catch (error) {

        console.error(
            "Failed to retrieve itinerary:",
            error
        );

        return res.status(500).json({
            error: "Failed to retrieve itinerary"
        });
    }
});

module.exports = router;