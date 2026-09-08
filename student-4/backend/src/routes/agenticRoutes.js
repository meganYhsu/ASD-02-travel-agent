const express = require("express");


const router = express.Router();

const {
    reviewItineraryWithOllama,
    updateItineraryWithOllama
} = require("../services/ollamaService");


router.post("/review", async (req, res) => {
    try {
        const {
            requirements,
            itinerary
        } = req.body;

        if (!requirements) {
            return res.status(400).json({
                success: false,
                error: "Trip requirements are required"
            });
        }

        if (!itinerary) {
            return res.status(400).json({
                success: false,
                error: "Generated itinerary is required"
            });
        }

        const review =
            await reviewItineraryWithOllama(
                requirements,
                itinerary
            );

        return res.status(200).json({
            success: true,
            data: review
        });

    } catch (error) {

        console.error(
            "Agentic review error:",
            error
        );

        return res.status(500).json({
            success: false,
            error: "Could not review itinerary"
        });
    }
});
router.post("/apply", async (req, res) => {
    try {
        const {
            itinerary,
            recommendedChanges
        } = req.body;

        if (!itinerary) {
            return res.status(400).json({
                success: false,
                error: "Itinerary is required"
            });
        }

        if (
            !Array.isArray(recommendedChanges) ||
            recommendedChanges.length === 0
        ) {
            return res.status(400).json({
                success: false,
                error: "Recommended changes are required"
            });
        }

        const userRequest =
            recommendedChanges.join("\n");

        const updatedItinerary =
            await updateItineraryWithOllama(
                itinerary,
                userRequest
            );

        return res.status(200).json({
            success: true,
            data: updatedItinerary
        });

    } catch (error) {
        console.error(
            "Ollama update error:",
            error
        );

        return res.status(500).json({
            success: false,
            error: "Could not update itinerary"
        });
    }
});


module.exports = router;

