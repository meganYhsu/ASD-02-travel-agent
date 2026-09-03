const fs = require("fs");
const path = require("path");

require("dotenv").config({
    path: path.resolve(__dirname, "../.env")
});




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

// const itineraryPromptTemplate = fs.readFileSync(
//     path.resolve(__dirname, "../prompts/generating_itinerary_prompt"),
//     "utf8"
// );
// // getting the prompt which is generating the lsit of cities:
// const cityListPrompt = fs.readFileSync(
//     path.resolve(__dirname , "../prompts/generate_city_list"),
//     "utf8"
// )

// making a neow variable which will store the prompt to generate different itineraries:
// const itineraries_options = fs.readFileSync(
//     path.resolve(__dirname , "../prompts/Getting_Itineraries_Options"),
//     "utf8"
// )
// // storing value from the BuildCOmpleteItinerary file:
// const build_complete_itinerary_p = fs.readFileSync(
//     path.resolve(__dirname , "../prompts/BuildCompleteItinerary"),
//     "utf8"
// )


//--------------------GETTING SYSTEM PROMPTS--------------------------------------

// const system_generate_itinerary_options_prompt = fs.readFileSync(
//     path.resolve(__dirname , "../prompts/system_prompts/generate_itinerary_options_system_prompt"),
//     "utf8"
// )
// const system_generate_complete_itinerary_prompt = fs.readFileSync(
//     path.resolve(__dirname , "../prompts/system_prompts/generate_complete_itinerary_system_prompt"),
//     "utf8"
// )



// function renderItineraryPrompt(details , promptTemplate) {
//     const destination = details.destination || "";
//     const startDate = details.startDate || "";
//     const endDate = details.endDate || "";
//     const budget = details.budget || "";
//     const group = details.group || details.travelGroup || "";
//     const travelStyle = details.travelStyle || "";
//     const travelPreference = details.travelPreference || "";
//     const cities = Array.isArray(details.c) ? details.c.join(", ") : "";
//     const selectedItinerary = details.selectedItinerary || "";
//
//     return promptTemplate
//         .replaceAll("${destination}", destination)
//         .replaceAll("${startDate}", startDate)
//         .replaceAll("${endDate}", endDate)
//         .replaceAll("${budget}", budget)
//         .replaceAll("${group}", group)
//         .replaceAll("${travelStyle}", travelStyle)
//         .replaceAll(
//             '${travelPreference || "No additional preferences provided"}',
//             travelPreference || "No additional preferences provided"
//         )
//         .replaceAll("${cities}", cities)
//         .replaceAll("${selectedItinerary}", JSON.stringify(selectedItinerary));
// }

// a function helping ot generate the list of the cities by replacing the destination :
// function generateCityList(destination , template){
//     return template
//         .replace("${destination}" , destination)
// }

// function compactItineraryForUpdate(itinerary) {
//     if (!itinerary || typeof itinerary !== "object") {
//         return {};
//     }
//
//     return {
//         title: itinerary.title || "",
//         summary: itinerary.summary || "",
//         estimatedCost: itinerary.estimatedCost || "",
//         currency: itinerary.currency || "",
//         days: Array.isArray(itinerary.days)
//             ? itinerary.days.map((day) => ({
//                 dayNumber: day.dayNumber,
//                 date: day.date,
//                 city: day.city,
//                 title: day.title,
//                 activities: Array.isArray(day.activities)
//                     ? day.activities.map((activity) => ({
//                         time: activity.time,
//                         name: activity.name
//                     }))
//                     : []
//             }))
//             : []
//     };
// }

// function buildRefinementInstruction(improvementPrompt) {
//     const prompt = String(improvementPrompt || "").trim();
//     if (!prompt) {
//         return "";
//     }
//
//     const lowerPrompt = prompt.toLowerCase();
//     const dietaryMatches = [];
//
//     if (lowerPrompt.includes("vegetarian")) {
//         dietaryMatches.push("Dietary requirement: vegetarian. All restaurant suggestions must be vegetarian-friendly and must not rely on meat or fish.");
//     }
//     if (lowerPrompt.includes("vegan")) {
//         dietaryMatches.push("Dietary requirement: vegan. All restaurant suggestions must be fully vegan and must not use dairy, eggs, meat, or fish.");
//     }
//     if (lowerPrompt.includes("halal")) {
//         dietaryMatches.push("Dietary requirement: halal. Restaurant suggestions must respect halal constraints.");
//     }
//     if (lowerPrompt.includes("kosher")) {
//         dietaryMatches.push("Dietary requirement: kosher. Restaurant suggestions must respect kosher constraints.");
//     }
//
//     return [prompt, ...dietaryMatches].join("\n");
// }

// function buildMinimalUpdatePrompt(details) {
//     const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
//     const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);
//     const destination = details.destination || "";
//     const startDate = details.startDate || "";
//     const endDate = details.endDate || "";
//     const budget = details.budget || "";
//     const group = details.group || "";
//     const travelStyle = details.travelStyle || "";
//     const travelPreference = details.travelPreference || "No additional preferences provided";
//     const cities = Array.isArray(details.c) ? details.c.join(", ") : "";
//     const refinementInstruction = buildRefinementInstruction(details.improvementPrompt || "");
//
//     return [
//         "You are updating an existing travel itinerary.",
//         "Keep the itinerary's overall structure, dates, and intent.",
//         "Return the full updated itinerary JSON only.",
//         "",
//         "Trip details:",
//         `Destination: ${destination}`,
//         `Start date: ${startDate}`,
//         `End date: ${endDate}`,
//         `Budget: ${budget} AUD`,
//         `Travelling with: ${group}`,
//         `Travel style: ${travelStyle}`,
//         `Selected cities: ${cities}`,
//         `Additional preferences: ${travelPreference}`,
//         "",
//         "Current itinerary JSON:",
//         JSON.stringify(compactSourceItinerary),
//         "",
//         "User change request:",
//         refinementInstruction,
//         "",
//         "The updated response must include:",
//         '{ "title": "", "summary": "", "estimatedCost": 0, "currency": "AUD", "days": [], "packingTips": [], "generalAdvice": [] }',
//         "Each day must include dayNumber, date, city, title, activities, restaurants, transportation, hotel, tips, badWeatherAlternative, and dailyBudget.",
//         "Restaurants must match any dietary restrictions in the request.",
//         "Do not add markdown or explanations."
//     ].join("\n");
// }
// a function that will take the itinerary and build the complete some:

// async function building_complete_itinerary_to_go(details, promptTemplate) {
//         const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
//         const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);
//
//         return promptTemplate
//             .replaceAll("${destination}", details.destination || "")
//             .replaceAll("${startDate}", details.startDate || "")
//             .replaceAll("${endDate}", details.endDate || "")
//             .replaceAll("${budget}", details.budget || "")
//             .replaceAll("${group}", details.group || "")
//             .replaceAll("${travelStyle}", details.travelStyle || "")
//             .replaceAll("${travelPreference || \"No additional preferences provided\"}", details.travelPreference || "No additional preferences provided")
//             .replaceAll("${cities}", Array.isArray(details.c) ? details.c.join(", ") : "")
//             .replaceAll("${selectedItinerary}", JSON.stringify(compactSourceItinerary));
// }



// app.post("/api/cities", async (req, res) => {
//     try {
//         const { destination } = req.body;
//
//         if (!destination) {
//             return res.status(400).json({
//                 error: "Destination is required"
//             });
//         }
//
//         // const prompt = `
//         // Give me the 10 most visited tourist cities in ${destination}.
//         //
//         // Return ONLY valid JSON in this format:
//         //
//         // {
//         //     "cities": [
//         //         "City 1",
//         //         "City 2",
//         //         "City 3"
//         //     ]
//         // }
//         //
//         // Do not include explanations.
//         // `;
//         const prompt = generateCityList(destination , cityListPrompt);
//
//
//         const response = await groq.chat.completions.create({
//             messages: [
//                 {
//                     role: "user",
//                     content: prompt
//                 }
//             ],
//             model: process.env.GROQ_MODEL
//         });
//
//         const aiResponse = response.choices[0].message.content;
//         const cities = JSON.parse(aiResponse);
//
//         res.json(cities);
//     } catch (error) {
//         console.error(error);
//         res.status(500).json({
//             error: "Could not generate cities"
//         });
//     }
// });

// app.post("/api/request_complete_itinerary", async (req, res) => {
//     try {
//         const details = req.body || {};
//
//         if (!details.destination || !details.startDate || !details.endDate || !details.budget || !details.travelStyle) {
//             return res.status(400).json({
//                 error: "Missing required trip details"
//             });
//         }
//
//         if (!Array.isArray(details.c) || details.c.length === 0) {
//             return res.status(400).json({
//                 error: "At least one city must be selected"
//             });
//         }
//
//         const prompt = renderItineraryPrompt(details , itineraryPromptTemplate);
//
//         const response = await groq.chat.completions.create({
//             model: process.env.GROQ_MODEL,
//             messages: [
//                 {
//                     role: "system",
//                     content: "You are an expert travel-planning assistant. Return only valid JSON."
//                 },
//                 {
//                     role: "user",
//                     content: prompt
//                 }
//             ],
//             response_format: {
//                 type: "json_object"
//             },
//             max_tokens: 2500
//         });
//
//         const content = response.choices?.[0]?.message?.content;
//
//         if (!content) {
//             return res.status(500).json({
//                 error: "Groq returned an empty response."
//             });
//         }
//
//         const parsedItinerary = JSON.parse(content);
//         return res.status(200).json(parsedItinerary);
//     } catch (error) {
//         console.error("Complete itinerary generation error:", error);
//         return res.status(500).json({
//             error: "An error occurred while generating the complete itinerary."
//         });
//     }
// });

// making anothe endpoint for the frontend to communicate with the backend:

// async function  generate_itineraries_options(req  , res ){
//     try{
//         const details = req.body|| {};
//         if (!details.destination || !details.startDate || !details.endDate || !details.budget || !details.travelStyle) {
//             return res.status(400).json({
//                 error: "Missing required trip details"
//             });
//         }
//         if (!Array.isArray(details.c) || details.c.length === 0) {
//             return res.status(400).json({
//                 error: "At least one city must be selected"
//             });
//         }
//     //     storing the prompt in a variable:
//         const prompt = renderItineraryPrompt(details , itineraries_options);
//         const resp = await groq.chat.completions.create({
//             model:process.env.GROQ_MODEL,
//             messages:[
//                 {
//                     role: "system" ,
//                     content: system_generate_itinerary_options_prompt
//                 },
//                 {
//                     role: "user" ,
//                     content: prompt
//                 }
//             ],
//             response_format:{type:"json_object"},
//             max_tokens:2500
//         })
//
//         const content = resp.choices[0].message.content;
//         if(!content){
//             return res.status(500).json({
//                 error:"Groq returned an empty array"
//             });
//         }
//         const parsedItineraries = JSON.parse(content);
//
//         console.log("Generated itineraries:");
//         console.log(parsedItineraries);
//
//         return res.status(200).json(parsedItineraries);
//
//     }
//     catch (error){
//         console.error("Complete itinerary generation error:", error);
//         return res.status(500).json({
//             error: "An error occurred while generating the complete itinerary."
//         });
//     }
// }

// // trying to make a function that will help to generate a complete itineray on the basis of the selected one:
// async function build_complete_itinerary(req , res){
//     try {
//         const details  = req.body || {};
//         const improvementPrompt = details.improvementPrompt || "";
//         const finalPrompt = improvementPrompt
//             ? buildMinimalUpdatePrompt(details)
//             : await building_complete_itinerary_to_go(details, build_complete_itinerary_p);
//
//         const resp = await groq.chat.completions.create({
//             model: process.env.GROQ_MODEL,
//             messages: [
//                 {
//                     role: "system",
//                     content: system_generate_complete_itinerary_prompt
//                 },
//                 {
//                     role: "user",
//                     content: finalPrompt
//                 }
//             ],
//             response_format: { type: "json_object" },
//             max_tokens: 5000
//         });
//
//         const content = resp.choices?.[0]?.message?.content;
//         if (!content) {
//             return res.status(500).json({
//                 error: "Groq returned an empty response."
//             });
//         }
//
//         const parsedItinerary = JSON.parse(content);
//         console.log("Generated itinerary:");
//         console.log(parsedItinerary);
//         return res.status(200).json(parsedItinerary);
//     } catch (error) {
//         console.error("Complete itinerary generation error:", error);
//         return res.status(500).json({
//             error: "An error occurred while generating the complete itinerary."
//         });
//     }
//
//
//
// }
// app.post("/api/request_itineraries" , generate_itineraries_options)
// // forming a pathway to call the above API:
// app.post("/api/generate_complete_selected_itinerary" , build_complete_itinerary)
//
// // making a new endpoint helping ot reviece request form the user's prompt
//
// app.post("/api/update_itinerary_from_prompt" , build_complete_itinerary)

app.listen(5001, () => {
    console.log("Backend running on port 5001");
});
