const express = require("express");
const router = express.Router();

const { updateItineraryFromFeedback } = require("../controllers/getFeedbackController");

router.post("/", updateItineraryFromFeedback);

module.exports = router;
