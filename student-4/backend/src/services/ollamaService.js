const OLLAMA_BASE_URL =
    process.env.OLLAMA_BASE_URL ||
    "http://localhost:11434/v1";

const OLLAMA_MODEL =
    process.env.OLLAMA_MODEL ||
    process.env.OLLAMA_USER_MODEL ||
    "llama3.1:8b";


async function reviewItineraryWithOllama(
    requirements,
    itinerary,
    approvedChanges = null
) {
    const reviewItinerary = {
        title: itinerary.title,
        summary: itinerary.summary,
        estimatedCost: itinerary.estimatedCost,
        currency: itinerary.currency,

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


    const controller =
        new AbortController();

    const timeout =
        setTimeout(() => {
            controller.abort();
        }, 60000);


    try {

        const response = await fetch(
            `${OLLAMA_BASE_URL}/chat/completions`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                signal: controller.signal,

                body: JSON.stringify({
                    model: OLLAMA_MODEL,

                    messages: [
                        {
                            role: "system",
                            content: `
You are a travel itinerary review agent.

You will receive:

1. The traveller's original requirements.
2. A generated travel itinerary.

Your job is ONLY to review the itinerary.

IMPORTANT REVIEW RULES:

DESTINATION:
- The destination may be a country, while the itinerary uses city names.
- Do NOT require the city name to equal the destination country name.
- Use the selected cities supplied in the requirements.
- If the itinerary uses the selected cities, treat the destination as satisfied.
- Example: destination "Australia" with selected cities
  ["Sydney", "Melbourne"] is valid if the itinerary contains
  Sydney and Melbourne.

BUDGET:
- The supplied budget is a MAXIMUM budget.
- An estimated cost below the budget is valid.
- Only report a budget problem when estimatedCost exceeds the budget.
- Example: budget 5000 AUD and estimatedCost 1200 AUD is valid.

TRAVEL GROUP:
- The itinerary does NOT need to literally mention the travel group.
- Judge whether the itinerary is suitable for that group.
- For example, an itinerary for "Friends" does not need to contain
  the word "friends".

TRAVEL STYLE:
- Do not require the itinerary title to contain the exact travel-style words.
- Judge the activities and pace of the itinerary.
- For example, "Cultural Travel" can be satisfied through museums,
  historical sites, local experiences and cultural attractions.

CITIES:
- Compare itinerary cities against requirements.cities.
- Do not flag a city merely because it is different from the destination
  country name.
  
USER-APPROVED CHANGES:
- The itinerary may contain changes explicitly requested by the user.
- Do NOT flag a condition as an issue if it is the direct result of an explicit user-approved change.
- For example, if the user explicitly requested that Day 4 have no activities, an empty Day 4 is valid.
- However, if a day is empty without being requested by the user, treat it as a potential issue.
- User-approved changes take priority unless they conflict with another explicit requirement, budget, date range, or safety constraint.

Check:
- dates
- budget
- selected cities
- travel style
- travel group
- special requirements
- practicality of the schedule
- overloaded days
- duplicate activities
- overall consistency

Do NOT invent issues.
Do NOT report a mismatch just because wording is different.
Only report an issue when there is a meaningful conflict.

Do NOT rewrite the itinerary.
Do NOT generate a replacement itinerary.

Return ONLY valid JSON using this structure:

{
  "valid": true,
  "summary": "Brief assessment of the itinerary",
  "issues": [],
  "recommendedChanges": []
}

The arrays may contain items depending on the review.
Do not copy example values literally.

If the itinerary satisfies the user's core requirements:
- valid must be true
- issues must be []
- summary must briefly explain why the itinerary is valid
- recommendedChanges may still contain useful optional improvements

Even when valid is true, review the itinerary for possible improvements in:
- pacing
- travel efficiency
- activity variety
- overloaded or underutilised days
- excessive travel between activities
- alignment with the selected travel style
- suitability for the travel group
- schedule practicality

Only add recommendedChanges when they would genuinely improve the itinerary.
Do not invent problems just to create recommendations.

If the itinerary has genuine problems or violates the user's requirements:
- valid must be false
- issues must list the genuine problems
- summary must briefly explain the main problems
- recommendedChanges must contain concise fixes for those problems

Do not return markdown.
Do not return anything outside the JSON.
`
                        },

                        {
                            role: "user",
                            content: `
ORIGINAL USER REQUIREMENTS:

${JSON.stringify(requirements)}

LATEST USER-APPROVED CHANGES:

${approvedChanges 
            ? JSON.stringify(approvedChanges)
            : "No additional user-approved changes were provided."}

CURRENT ITINERARY:

${JSON.stringify(reviewItinerary)}

Review this itinerary.
`
                        }
                    ],

                    temperature: 0.1,
                    max_tokens: 700
                })
            }
        );


        if (!response.ok) {
            const error =
                await response.text();

            throw new Error(
                `Ollama review failed: ${response.status} ${error}`
            );
        }


        const data =
            await response.json();

        const content =
            data.choices?.[0]?.message?.content;


        if (!content) {
            throw new Error(
                "Ollama returned an empty review"
            );
        }


        const cleanedContent =
            content
                .replace(/```json/gi, "")
                .replace(/```/g, "")
                .trim();


        return JSON.parse(
            cleanedContent
        );


    } catch (error) {

        if (error.name === "AbortError") {
            throw new Error(
                "Ollama review timed out after 60 seconds"
            );
        }

        throw error;

    } finally {

        clearTimeout(timeout);

    }
}


async function updateItineraryWithOllama(
    currentItinerary,
    userRequest
) {
    // Send Ollama only the information it needs
    const compactItinerary = {
        title: currentItinerary.title,
        summary: currentItinerary.summary,
        estimatedCost: currentItinerary.estimatedCost,
        currency: currentItinerary.currency,

        days: Array.isArray(currentItinerary.days)
            ? currentItinerary.days.map((day) => ({
                dayNumber: day.dayNumber,
                date: day.date,
                city: day.city,
                title: day.title,

                activities: Array.isArray(day.activities)
                    ? day.activities.map((activity) => ({
                        time: activity.time,
                        name: activity.name,
                        description: activity.description
                    }))
                    : []
            }))
            : []
    };


    const controller = new AbortController();

    const timeout = setTimeout(() => {
        controller.abort();
    }, 600000);


    try {

        const response = await fetch(
            `${OLLAMA_BASE_URL}/chat/completions`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                signal: controller.signal,

                body: JSON.stringify({
                    model: OLLAMA_MODEL,

                    messages: [
                        {
                            role: "system",
                            content: `
You are a travel itinerary update agent.

A human has approved recommended changes
to an existing itinerary.

Apply ONLY the approved changes.

IMPORTANT:

Do NOT regenerate the entire itinerary.

Return ONLY the days that actually need changing.

Return valid JSON in exactly this format:

{
    "updatedDays": [
        {
            "dayNumber": 1,
            "date": "",
            "city": "",
            "title": "",
            "activities": [
                {
                    "time": "",
                    "name": "",
                    "description": ""
                }
            ]
        }
    ]
}

If only Day 4 needs changing,
return ONLY Day 4.

Preserve all other days by not returning them.

Do not return markdown.
Do not return anything outside the JSON.
`
                        },

                        {
                            role: "user",
                            content: `
CURRENT ITINERARY:

${JSON.stringify(compactItinerary)}

HUMAN-APPROVED CHANGES:

${userRequest}

Return only the days that require modification.
`
                        }
                    ],

                    temperature: 0.1,
                    max_tokens: 1200
                })
            }
        );


        if (!response.ok) {
            const error = await response.text();

            throw new Error(
                `Ollama update failed: ${response.status} ${error}`
            );
        }


        const data = await response.json();

        const content =
            data.choices?.[0]?.message?.content;

        if (!content) {
            throw new Error(
                "Ollama returned an empty update"
            );
        }


        const cleanedContent = content
            .replace(/```json/gi, "")
            .replace(/```/g, "")
            .trim();


        const update =
            JSON.parse(cleanedContent);


        if (!Array.isArray(update.updatedDays)) {
            throw new Error(
                "Ollama did not return updatedDays"
            );
        }


        // Merge Ollama's changed days into
        // the original itinerary.
        const updatedItinerary = {
            ...currentItinerary,

            days: Array.isArray(currentItinerary.days)
                ? currentItinerary.days.map((originalDay) => {

                    const changedDay =
                        update.updatedDays.find(
                            (day) =>
                                day.dayNumber === originalDay.dayNumber
                        );

                    if (!changedDay) {
                        return originalDay;
                    }

                    return {
                        ...originalDay,
                        ...changedDay
                    };
                })
                : []
        };


        return updatedItinerary;


    } catch (error) {

        if (error.name === "AbortError") {
            throw new Error(
                "Ollama update timed out after 600 seconds"
            );
        }

        throw error;

    } finally {

        clearTimeout(timeout);
    }
}


module.exports = {
    reviewItineraryWithOllama,
    updateItineraryWithOllama,

};


