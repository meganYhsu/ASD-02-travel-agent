// const {
//     updateItineraryWithOllama
// } = require("../services/ollamaService");
//
// function validateUpdatedItinerary(itinerary) {
//     const problems = [];
//
//     if (!itinerary || typeof itinerary !== "object") {
//         problems.push("Response is not an object");
//         return problems;
//     }
//
//     if (!itinerary.title) {
//         problems.push("Missing title");
//     }
//
//     if (!itinerary.summary) {
//         problems.push("Missing summary");
//     }
//
//     if (!Array.isArray(itinerary.days)) {
//         problems.push("Missing days array");
//     }
//
//     if (
//         Array.isArray(itinerary.days) &&
//         itinerary.days.length === 0
//     ) {
//         problems.push("Days array is empty");
//     }
//
//     return problems;
// }
//
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
//
// function normalizeUpdatedItinerary(updatedItinerary, sourceItinerary = {}) {
//     if (!updatedItinerary || typeof updatedItinerary !== "object") {
//         return {};
//     }
//
//     return {
//         ...updatedItinerary,
//         estimatedCost: updatedItinerary.estimatedCost ?? sourceItinerary.estimatedCost ?? 0,
//         currency: updatedItinerary.currency || sourceItinerary.currency || "AUD"
//     };
// }
//
// function buildFeedbackPrompt(details) {
//     const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
//     const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);
//     const feedback = String(details.feedback || details.improvementPrompt || "").trim();
//
//     return [
//         "You are updating an existing travel itinerary based on user feedback.",
//         "Return the full updated itinerary JSON only.",
//         "",
//         "Current itinerary JSON:",
//         JSON.stringify(compactSourceItinerary),
//         "",
//         "User feedback:",
//         feedback,
//         "",
//         "The updated response must include:",
//         '{ "title": "", "summary": "", "estimatedCost": 0, "currency": "AUD", "days": [], "packingTips": [], "generalAdvice": [] }',
//         "Do not add markdown or explanations."
//     ].join("\n");
// }
//
// async function updateItineraryFromFeedback(req, res) {
//     try {
//         const details = req.body || {};
//
//         if (!details.currentItinerary && !details.selectedItinerary) {
//             return res.status(400).json({ error: "Current itinerary is required" });
//         }
//
//         if (!details.improvementPrompt && !details.feedback) {
//             return res.status(400).json({ error: "Feedback is required" });
//         }
//
//         const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
//         const finalPrompt = buildFeedbackPrompt(details);
//         const content = await updateItineraryWithOllama(sourceItinerary, finalPrompt);
//
//         if (!content) {
//             return res.status(500).json({ error: "Ollama returned an empty response" });
//         }
//
//         let parsedItinerary;
//         try {
//             parsedItinerary = JSON.parse(content);
//         } catch (parseError) {
//             return res.status(500).json({
//                 error: "Ollama returned invalid JSON",
//                 details: parseError.message
//             });
//         }
//
//         const normalizedItinerary = normalizeUpdatedItinerary(parsedItinerary, sourceItinerary);
//         const validationProblems = validateUpdatedItinerary(normalizedItinerary);
//
//         if (validationProblems.length > 0) {
//             return res.status(502).json({
//                 error: "Ollama returned an incomplete itinerary",
//                 problems: validationProblems
//             });
//         }
//
//         return res.status(200).json(normalizedItinerary);
//
//         // PLAN
// //         const feedback = String(
// //             details.feedback ||
// //             details.improvementPrompt ||
// //             ""
// //         ).trim();
// //
// //         const plan = {
// //             goal: feedback,
// //             currentItinerary:
// //                 compactItineraryForUpdate(sourceItinerary)
// //         };
// //
// //         let adaptationFeedback = "";
// //
// //         const MAX_ATTEMPTS = 2;
// //
// //         for (
// //             let attempt = 1;
// //             attempt <= MAX_ATTEMPTS;
// //             attempt++
// //         ) {
// //
// //             // ACT
// //             let requestToAI = plan.goal;
// //
// //             if (adaptationFeedback) {
// //                 requestToAI += `
// //
// // The previous response failed validation.
// //
// // Problems:
// // ${adaptationFeedback}
// //
// // Fix these problems and return the complete itinerary as valid JSON.
// // `;
// //             }
// //
// //             const content =
// //                 await updateItineraryWithOllama(
// //                     plan.currentItinerary,
// //                     requestToAI
// //                 );
// //
// //
// //             // OBSERVE
// //             if (!content) {
// //                 adaptationFeedback =
// //                     "The model returned an empty response.";
// //
// //                 continue;
// //             }
// //
// //             let updatedItinerary;
// //
// //             try {
// //                 updatedItinerary = JSON.parse(content);
// //             } catch {
// //                 adaptationFeedback =
// //                     "The model did not return valid JSON.";
// //
// //                 continue;
// //             }
// //
// //             updatedItinerary =
// //                 normalizeUpdatedItinerary(
// //                     updatedItinerary,
// //                     sourceItinerary
// //                 );
// //
// //             const problems =
// //                 validateUpdatedItinerary(
// //                     updatedItinerary
// //                 );
// //
// //             if (problems.length === 0) {
// //                 return res.status(200).json(
// //                     updatedItinerary
// //                 );
// //             }
// //
// //
// //             // ADAPT
// //             adaptationFeedback =
// //                 problems.join("; ");
// //         }
// //
// //         return res.status(502).json({
// //             error:
// //                 "Ollama could not generate a valid itinerary after retrying"
// //         });
//         } catch (error) {
//             console.error("Feedback update error:", error);
//             return res.status(500).json({ error: "Could not update itinerary" });
//         }
//
// }
//
// module.exports = {
//     updateItineraryFromFeedback
// };

const {
    updateItineraryWithOllama
} = require("../services/ollamaService");

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

function buildFeedbackPrompt(details) {
    const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
    const compactSourceItinerary = compactItineraryForUpdate(sourceItinerary);
    const feedback = String(details.feedback || details.improvementPrompt || "").trim();

    return [
        "You are updating an existing travel itinerary based on user feedback.",
        "Return the full updated itinerary JSON only.",
        "",
        "Current itinerary JSON:",
        JSON.stringify(compactSourceItinerary),
        "",
        "User feedback:",
        feedback,
        "",
        "The updated response must include:",
        '{ "title": "", "summary": "", "estimatedCost": 0, "currency": "AUD", "days": [], "packingTips": [], "generalAdvice": [] }',
        "Do not add markdown or explanations."
    ].join("\n");
}

async function updateItineraryFromFeedback(req, res) {
    try {
        const details = req.body || {};

        if (!details.currentItinerary && !details.selectedItinerary) {
            return res.status(400).json({ error: "Current itinerary is required" });
        }

        if (!details.improvementPrompt && !details.feedback) {
            return res.status(400).json({ error: "Feedback is required" });
        }

        const sourceItinerary = details.currentItinerary || details.selectedItinerary || {};
        const finalPrompt = buildFeedbackPrompt(details);
        const content = await updateItineraryWithOllama(sourceItinerary, finalPrompt);

        if (!content) {
            return res.status(500).json({ error: "Ollama returned an empty response" });
        }

        return res.status(200).json(normalizeUpdatedItinerary(JSON.parse(content), sourceItinerary));
    } catch (error) {
        console.error("Feedback update error:", error);
        return res.status(500).json({ error: "Could not update itinerary" });
    }
}

module.exports = {
    updateItineraryFromFeedback
};




