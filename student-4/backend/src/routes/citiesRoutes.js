const express = require("express")
const router = express.Router();

const{
    generateCitiesList
} = require("../controllers/cityController");

router.post("/cities", generateCitiesList);

module.exports = router;