const express = require("express");
const router = express.Router();

const {
    generateItineraryOptions,
    generateCompleteItinerary,
    updateItinerary,
    saveGeneratedItinerary,
    getSavedItinerary,
    deleteSavedItinerary
} = require("../controllers/itineraryController");


// 1. Generate multiple itinerary options
router.post(
    "/request_itineraries",
    generateItineraryOptions
);


// 2. Generate full itinerary from selected option
router.post(
    "/generate_complete_selected_itinerary",
    generateCompleteItinerary
);


// 3. Update the already generated itinerary
// router.post(
//     "/update_itinerary_from_prompt",
//     updateItinerary
// );



// 4. Save the generated itinerary to the database service
router.post(
    "/save_itinerary",
    saveGeneratedItinerary
);

router.get(
    "/saved_itineraries/:id",
    getSavedItinerary
);

router.delete(
    "/saved_itineraries/:id",
    deleteSavedItinerary
);


module.exports = router;
