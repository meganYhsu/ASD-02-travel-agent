const fs = require("fs");
const path = require("path");

require("dotenv").config({
    path: path.resolve(__dirname, "../.env")
});

const {
    getItinerary,
    DatabaseUnavailableError
} = require("../src/services/DBService.js");



const Groq = require("groq-sdk");
const express = require("express");
const cors = require("cors");

const app = express();

app.use(cors());
app.use(express.json());

const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY
});

const cityRoutes = require("./routes/citiesRoutes");

app.use("/api", cityRoutes);

const itineraryRoutes =
    require("./routes/getItineraryRoute");

app.use("/api", itineraryRoutes);

const feedbackRoutes =
    require("./routes/getFeedbackRoute");

app.use("/api/update_itinerary_from_prompt", feedbackRoutes);



const agenticRoutes =
    require("./routes/agenticRoutes");

const ollamaRoutes =
    require("./routes/ollamaRoutes");

app.use("/api/agentic", agenticRoutes);
app.use(
    "/api/ollama",
    ollamaRoutes
);
// app.get("/api/agentic/status", async (req, res) => {
//     const itineraryId = req.query.itineraryId;
//
//     if (!itineraryId) {
//         return res.status(400).json({
//             success: false,
//             error: "itineraryId is required"
//         });
//     }
//
//     try {
//         const response = await getItinerary(itineraryId);
//
//         // Depending on your database response format
//         const itinerary = response.data || response;
//
//         const days = Array.isArray(itinerary.days)
//             ? itinerary.days
//             : [];
//
//         const activities = days.flatMap((day) =>
//             Array.isArray(day.activities)
//                 ? day.activities
//                 : []
//         );
//
//         // OBSERVE
//         const activitiesWithoutTime =
//             activities.filter(
//                 (activity) => !activity.time
//             );
//
//         const activitiesWithoutLocation =
//             activities.filter(
//                 (activity) => !activity.location && !activity.name
//             );
//
//         // ADAPT
//         const adaptActions = [];
//
//         if (days.length === 0) {
//             adaptActions.push(
//                 "Generate itinerary days."
//             );
//         }
//
//         if (activitiesWithoutTime.length > 0) {
//             adaptActions.push(
//                 "Add missing times to itinerary activities."
//             );
//         }
//
//         if (activitiesWithoutLocation.length > 0) {
//             adaptActions.push(
//                 "Review activities with missing location information."
//             );
//         }
//
//         if (adaptActions.length === 0) {
//             adaptActions.push(
//                 "No adaptation required. The itinerary is currently complete."
//             );
//         }
//
//         return res.status(200).json({
//             success: true,
//
//             data: {
//                 plan: {
//                     destination:
//                         itinerary.destination || null,
//
//                     travelStyle:
//                         itinerary.travelStyle || null,
//
//                     startDate:
//                         itinerary.startDate || null,
//
//                     endDate:
//                         itinerary.endDate || null
//                 },
//
//                 act: {
//                     itineraryCreated: true,
//                     totalDays: days.length,
//                     totalActivities: activities.length
//                 },
//
//                 observe: {
//                     activitiesWithoutTime:
//                     activitiesWithoutTime.length,
//
//                     activitiesWithoutLocation:
//                     activitiesWithoutLocation.length
//                 },
//
//                 adapt: {
//                     recommendedNextSteps:
//                     adaptActions
//                 }
//             }
//         });
//
//     } catch (error) {
//
//         if (error instanceof DatabaseUnavailableError) {
//             return res.status(503).json({
//                 success: false,
//                 error: "Database service unavailable"
//             });
//         }
//
//         console.error(
//             "Agentic status error:",
//             error
//         );
//
//         return res.status(500).json({
//             success: false,
//             error: "Could not determine agentic status"
//         });
//     }
// });

app.get("/api/agentic/status", async (req, res) => {
    const itineraryId = req.query.itineraryId;

    if (!itineraryId) {
        return res.status(400).json({
            success: false,
            error: "itineraryId is required"
        });
    }

    try {
        const response = await getItinerary(itineraryId);

        /*
         * Database API returns:
         *
         * {
         *   itinerary: {...},
         *   activities: [...]
         * }
         */
        const data = response.data || response;

        const itinerary =
            data.itinerary || data;

        const activities =
            Array.isArray(data.activities)
                ? data.activities
                : [];

        const dayNumbers = new Set(
            activities
                .map(activity => activity.day_no)
                .filter(dayNo => dayNo !== null && dayNo !== undefined)
        );

        const totalDays = dayNumbers.size;


        // -------------------------
        // OBSERVE
        // -------------------------

        const activitiesWithoutTime =
            activities.filter(
                activity => !activity.time
            );

        const activitiesWithoutLocation =
            activities.filter(
                activity => !activity.location
            );


        // -------------------------
        // ADAPT
        // -------------------------

        const adaptActions = [];

        if (totalDays === 0) {
            adaptActions.push(
                "Generate itinerary days."
            );
        }

        if (activitiesWithoutTime.length > 0) {
            adaptActions.push(
                "Add missing times to itinerary activities."
            );
        }

        if (activitiesWithoutLocation.length > 0) {
            adaptActions.push(
                "Review activities with missing location information."
            );
        }

        if (adaptActions.length === 0) {
            adaptActions.push(
                "No adaptation required. The itinerary is currently complete."
            );
        }


        return res.status(200).json({
            success: true,

            data: {

                // PLAN
                plan: {
                    destination:
                        itinerary.destination || null,

                    travelStyle:
                        itinerary.travel_style || null,

                    startDate:
                        itinerary.start_date || null,

                    endDate:
                        itinerary.end_date || null
                },


                // ACT
                act: {
                    itineraryCreated:
                        Boolean(itinerary.itinerary_id),

                    totalDays,

                    totalActivities:
                    activities.length
                },


                // OBSERVE
                observe: {
                    activitiesWithoutTime:
                    activitiesWithoutTime.length,

                    activitiesWithoutLocation:
                    activitiesWithoutLocation.length
                },


                // ADAPT
                adapt: {
                    recommendedNextSteps:
                    adaptActions
                }
            }
        });

    } catch (error) {

        if (error instanceof DatabaseUnavailableError) {
            return res.status(503).json({
                success: false,
                error: "Database service unavailable"
            });
        }

        console.error(
            "Agentic status error:",
            error
        );

        return res.status(500).json({
            success: false,
            error: "Could not determine agentic status"
        });
    }
});

app.listen(5001, () => {
    console.log("Backend running on port 5001");
});
