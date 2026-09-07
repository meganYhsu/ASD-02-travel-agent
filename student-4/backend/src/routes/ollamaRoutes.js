const express = require("express");

const {
    generateItineraryWithOllama
} = require("../services/ollamaService");

const router = express.Router();


router.post("/generate-itinerary", async (req, res) => {

    try {

        const tripDetails = req.body;

        if (
            !tripDetails.destination ||
            !tripDetails.startDate ||
            !tripDetails.endDate
        ) {
            return res.status(400).json({
                success: false,
                error: "Missing required trip details"
            });
        }

        const itinerary =
            await generateItineraryWithOllama(
                tripDetails
            );

        return res.status(200).json({
            success: true,
            data: itinerary
        });

    } catch (error) {

        console.error(
            "Ollama generation error:",
            error
        );

        return res.status(500).json({
            success: false,
            error: "Could not generate itinerary"
        });
    }
});


module.exports = router;