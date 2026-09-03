    const Groq = require("groq-sdk");
const fs = require("fs");
const path = require("path");
const {
    saveItinerary,
    saveActivity,
    getItinerary,
    deleteItinerary
} = require("../services/DBService");

const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY
});
//
// const {
//     // renderItineraryPrompt,
//     // buildingCompleteItinerary,
//     // buildMinimalUpdatePrompt
// } = require("../utils/itineraryHelpers");


function renderItineraryPrompt(details , promptTemplate) {
    const destination = details.destination || "";
    const startDate = details.startDate || "";
    const endDate = details.endDate || "";
    const budget = details.budget || "";
    const group = details.group || details.travelGroup || "";
    const travelStyle = details.travelStyle || "";
    const travelPreference = details.travelPreference || "";
    const cities = Array.isArray(details.c) ? details.c.join(", ") : "";
    const selectedItinerary = details.selectedItinerary || "";
    return promptTemplate
        .replaceAll("${destination}", destination)
        .replaceAll("${startDate}", startDate)
        .replaceAll("${endDate}", endDate)
        .replaceAll("${budget}", budget)
        .replaceAll("${group}", group)
        .replaceAll("${travelStyle}", travelStyle)
        .replaceAll(
            '${travelPreference || "No additional preferences provided"}',
            travelPreference || "No additional preferences provided"
        )
        .replaceAll("${cities}", cities)
        .replaceAll("${selectedItinerary}", JSON.stringify(selectedItinerary));
}

function compactItineraryForUpdate(itinerary) {
    if (!itinerary || typeof itinerary !== "object") {
        return {};
    }

    return {
        title: itinerary.title || "",
        summary: itinerary.summary || "",
        estimatedCost: itinerary.estimatedCost || "",
        currency: itinerary.currency || "",
        days: Array.isArray(itinerary.days)
            ? itinerary.days.map((day) => ({
                dayNumber: day.dayNumber,
                date: day.date,
                city: day.city,
                title: day.title,
                activities: Array.isArray(day.activities)
                    ? day.activities.map((activity) => ({
                        time: activity.time,
                        name: activity.name
                    }))
                    : []
            }))
            : []
    };
}

function normalizeUpdatedItinerary(updatedItinerary, sourceItinerary = {}) {
    if (!updatedItinerary || typeof updatedItinerary !== "object") {
        return {};
    }

    return {
        ...updatedItinerary,
        estimatedCost: updatedItinerary.estimatedCost ?? sourceItinerary.estimatedCost ?? 0,
        currency: updatedItinerary.currency || sourceItinerary.currency || "AUD"
    };
}

function buildRefinementInstruction(improvementPrompt) {
    const prompt = String(improvementPrompt || "").trim();
    if (!prompt) {
        return "";
    }

    const lowerPrompt = prompt.toLowerCase();
    const dietaryMatches = [];

    if (lowerPrompt.includes("vegetarian")) {
        dietaryMatches.push("Dietary requirement: vegetarian. All restaurant suggestions must be vegetarian-friendly and must not rely on meat or fish.");
    }
    if (lowerPrompt.includes("vegan")) {
        dietaryMatches.push("Dietary requirement: vegan. All restaurant suggestions must be fully vegan and must not use dairy, eggs, meat, or fish.");
    }
    if (lowerPrompt.includes("halal")) {
        dietaryMatches.push("Dietary requirement: halal. Restaurant suggestions must respect halal constraints.");
    }
    if (lowerPrompt.includes("kosher")) {
        dietaryMatches.push("Dietary requirement: kosher. Restaurant suggestions must respect kosher constraints.");
    }

    return [prompt, ...dietaryMatches].join("\n");
}

async function building_complete_itinerary_to_go(details, promptTemplate) {
    const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
    const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);

    return promptTemplate
        .replaceAll("${destination}", details.destination || "")
        .replaceAll("${startDate}", details.startDate || "")
        .replaceAll("${endDate}", details.endDate || "")
        .replaceAll("${budget}", details.budget || "")
        .replaceAll("${group}", details.group || "")
        .replaceAll("${travelStyle}", details.travelStyle || "")
        .replaceAll("${travelPreference || \"No additional preferences provided\"}", details.travelPreference || "No additional preferences provided")
        .replaceAll("${cities}", Array.isArray(details.c) ? details.c.join(", ") : "")
        .replaceAll("${selectedItinerary}", JSON.stringify(compactSourceItinerary));
}


function buildMinimalUpdatePrompt(details) {
    const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
    const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);
    const destination = details.destination || "";
    const startDate = details.startDate || "";
    const endDate = details.endDate || "";
    const budget = details.budget || "";
    const group = details.group || "";
    const travelStyle = details.travelStyle || "";
    const travelPreference = details.travelPreference || "No additional preferences provided";
    const cities = Array.isArray(details.c) ? details.c.join(", ") : "";
    const refinementInstruction = buildRefinementInstruction(details.improvementPrompt || "");

    return [
        "You are updating an existing travel itinerary.",
        "Keep the itinerary's overall structure, dates, and intent.",
        "Return the full updated itinerary JSON only.",
        "",
        "Trip details:",
        `Destination: ${destination}`,
        `Start date: ${startDate}`,
        `End date: ${endDate}`,
        `Budget: ${budget} AUD`,
        `Travelling with: ${group}`,
        `Travel style: ${travelStyle}`,
        `Selected cities: ${cities}`,
        `Additional preferences: ${travelPreference}`,
        "",
        "Current itinerary JSON:",
        JSON.stringify(compactSourceItinerary),
        "",
        "User change request:",
        refinementInstruction,
        "",
        "The updated response must include:",
        '{ "title": "", "summary": "", "estimatedCost": 0, "currency": "AUD", "days": [], "packingTips": [], "generalAdvice": [] }',
        "Each day must include dayNumber, date, city, title, activities, restaurants, transportation, hotel, tips, badWeatherAlternative, and dailyBudget.",
        "Restaurants must match any dietary restrictions in the request.",
        "Do not add markdown or explanations."
    ].join("\n");
}

function buildDatabaseActivityRows(itinerary) {
    if (!itinerary || !Array.isArray(itinerary.days)) {
        return [];
    }

    const rows = [];

    itinerary.days.forEach((day, index) => {
        const dayNo = Number.isInteger(day?.dayNumber) ? day.dayNumber : index + 1;
        const date = day?.date || "";
        const location = day?.city || day?.location || "";

        if (Array.isArray(day?.activities)) {
            day.activities.forEach((activity) => {
                rows.push({
                    dayNo,
                    date,
                    location,
                    time: activity?.time || "00:00",
                    cost: activity?.cost || "",
                    note: [
                        activity?.name,
                        activity?.description
                    ].filter(Boolean).join(" - ")
                });
            });
        }

        if (Array.isArray(day?.restaurants)) {
            day.restaurants.forEach((restaurant) => {
                rows.push({
                    dayNo,
                    date,
                    location,
                    time: restaurant?.meal || "Meal",
                    cost: restaurant?.estimatedCost || "",
                    note: restaurant?.name || ""
                });
            });
        }
    });

    return rows;
}









// const {
//     itinerariesOptionsPrompt,
//     completeItineraryPrompt,
//     systemGenerateOptionsPrompt,
//     systemGenerateCompletePrompt
// } = require("../config/prompts");

const itineraryPromptTemplate = fs.readFileSync(
    path.resolve(__dirname, "../../prompts/generating_itinerary_prompt"),
    "utf8"
);
// getting the prompt which is generating the lsit of cities:
const cityListPrompt = fs.readFileSync(
    path.resolve(__dirname , "../../prompts/generate_city_list"),
    "utf8"
)


const itineraries_options = fs.readFileSync(
    path.resolve(__dirname , "../../prompts/Getting_Itineraries_Options"),
    "utf8"
)
const build_complete_itinerary_p = fs.readFileSync(
    path.resolve(__dirname , "../../prompts/BuildCompleteItinerary"),
    "utf8"
)

const system_generate_itinerary_options_prompt = fs.readFileSync(
    path.resolve(__dirname , "../../prompts/system_prompts/generate_itinerary_options_system_prompt"),
    "utf8"
)
const system_generate_complete_itinerary_prompt = fs.readFileSync(
    path.resolve(__dirname , "../../prompts/system_prompts/generate_complete_itinerary_system_prompt"),
    "utf8"
)



// --------------------------------------------------
// 1. GENERATE ITINERARY OPTIONS
// --------------------------------------------------

async function  generate_itineraries_options(req  , res ){
    try{
        const details = req.body|| {};
        if (!details.destination || !details.startDate || !details.endDate || !details.budget || !details.travelStyle) {
            return res.status(400).json({
                error: "Missing required trip details"
            });
        }
        if (!Array.isArray(details.c) || details.c.length === 0) {
            return res.status(400).json({
                error: "At least one city must be selected"
            });
        }
        //     storing the prompt in a variable:
        const prompt = renderItineraryPrompt(details , itineraries_options);
        const resp = await groq.chat.completions.create({
            model:process.env.GROQ_MODEL,
            messages:[
                {
                    role: "system" ,
                    content: system_generate_itinerary_options_prompt
                },
                {
                    role: "user" ,
                    content: prompt
                }
            ],
            response_format:{type:"json_object"},
            max_tokens:2500
        })

        const content = resp.choices[0].message.content;
        if(!content){
            return res.status(500).json({
                error:"Groq returned an empty array"
            });
        }
        const parsedItineraries = JSON.parse(content);

        console.log("Generated itineraries:");
        console.log(parsedItineraries);

        return res.status(200).json(parsedItineraries);

    }
    catch (error){
        console.error("Complete itinerary generation error:", error);
        return res.status(500).json({
            error: "An error occurred while generating the complete itinerary."
        });
    }
}


// --------------------------------------------------
// 2. GENERATE COMPLETE SELECTED ITINERARY
// --------------------------------------------------

async function build_complete_itinerary(req , res){
    try {
        const details  = req.body || {};
        const improvementPrompt = details.improvementPrompt || "";
        const finalPrompt = improvementPrompt
            ? buildMinimalUpdatePrompt(details)
            : await building_complete_itinerary_to_go(details, build_complete_itinerary_p);

        const resp = await groq.chat.completions.create({
            model: process.env.GROQ_MODEL,
            messages: [
                {
                    role: "system",
                    content: system_generate_complete_itinerary_prompt
                },
                {
                    role: "user",
                    content: finalPrompt
                }
            ],
            response_format: { type: "json_object" },
            max_tokens: 5000
        });

        const content = resp.choices?.[0]?.message?.content;
        if (!content) {
            return res.status(500).json({
                error: "Groq returned an empty response."
            });
        }

        const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
        const parsedItinerary = normalizeUpdatedItinerary(JSON.parse(content), sourceItinerary);
        console.log("Generated itinerary:");
        console.log(parsedItinerary);
        return res.status(200).json(parsedItinerary);
    } catch (error) {
        console.error("Complete itinerary generation error:", error);
        return res.status(500).json({
            error: "An error occurred while generating the complete itinerary."
        });
    }



}


// --------------------------------------------------
// 3. UPDATE ITINERARY FROM USER PROMPT
// --------------------------------------------------

async function updateItinerary(req, res) {
    try {
        const details = req.body || {};

        if (!details.improvementPrompt) {
            return res.status(400).json({
                error: "Improvement prompt is required"
            });
        }

        if (
            !details.currentItinerary &&
            !details.selectedItinerary
        ) {
            return res.status(400).json({
                error: "Current itinerary is required"
            });
        }

        const finalPrompt =
            buildMinimalUpdatePrompt(details);

        const response = await groq.chat.completions.create({
            model: process.env.GROQ_MODEL,

            messages: [
                {
                    role: "system",
            content: system_generate_complete_itinerary_prompt
                },
                {
                    role: "user",
                    content: finalPrompt
                }
            ],

            response_format: {
                type: "json_object"
            },

            max_tokens: 5000
        });

        const content =
            response.choices?.[0]?.message?.content;

        if (!content) {
            return res.status(500).json({
                error: "Groq returned an empty response"
            });
        }

        const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
        const updatedItinerary = normalizeUpdatedItinerary(JSON.parse(content), sourceItinerary);

        return res.status(200).json(updatedItinerary);

    } catch (error) {
        console.error(
            "Itinerary update error:",
            error
        );

        return res.status(500).json({
            error: "Could not update itinerary"
        });
    }
}

async function saveGeneratedItinerary(req, res) {
    try {
        const details = req.body || {};
        const sourceItinerary = details.currentItinerary || details.selectedItinerary;

        if (!sourceItinerary) {
            return res.status(400).json({
                error: "Current itinerary is required"
            });
        }

        const itineraryResult = await saveItinerary({
            destination: details.destination,
            startDate: details.startDate,
            endDate: details.endDate,
            budget: details.budget,
            travelGroup: details.group || details.travelGroup,
            travelStyle: details.travelStyle,
            requirements: details.travelPreference || details.requirements || ""
        });

        const itineraryId = itineraryResult.itineraryId;
        const activityRows = buildDatabaseActivityRows(sourceItinerary);

        for (const activity of activityRows) {
            await saveActivity(itineraryId, activity);
        }

        return res.status(201).json({
            itineraryId,
            savedActivities: activityRows.length
        });
    } catch (error) {
        console.error("Itinerary save error:", error);
        return res.status(500).json({
            error: "Could not save itinerary"
        });
    }
}

async function getSavedItinerary(req, res) {
    try {
        const itineraryId = Number(req.params.id);

        if (!Number.isInteger(itineraryId)) {
            return res.status(400).json({
                error: "Invalid itinerary id"
            });
        }

        const data = await getItinerary(itineraryId);
        if (!data) {
            return res.status(404).json({
                error: "Itinerary not found"
            });
        }

        return res.status(200).json(data);
    } catch (error) {
        console.error("Load saved itinerary error:", error);
        return res.status(500).json({
            error: "Could not load itinerary"
        });
    }
}

async function deleteSavedItinerary(req, res) {
    try {
        const itineraryId = Number(req.params.id);

        if (!Number.isInteger(itineraryId)) {
            return res.status(400).json({
                error: "Invalid itinerary id"
            });
        }

        await deleteItinerary(itineraryId);
        return res.status(200).json({ ok: true, deletedItineraryId: itineraryId });
    } catch (error) {
        console.error("Delete saved itinerary error:", error);
        return res.status(500).json({
            error: "Could not delete itinerary"
        });
    }
}


module.exports = {
    generateItineraryOptions: generate_itineraries_options,
    generateCompleteItinerary: build_complete_itinerary,
    updateItinerary,
    saveGeneratedItinerary,
    getSavedItinerary,
    deleteSavedItinerary
};
