const OLLAMA_BASE_URL =
    process.env.OLLAMA_BASE_URL ||
    "http://localhost:11434/v1";

const OLLAMA_MODEL =
    process.env.OLLAMA_MODEL ||
    process.env.OLLAMA_USER_MODEL ||
    "llama3.1:8b";


async function updateItineraryWithOllama(
    currentItinerary,
    userRequest
) {
    const response = await fetch(
        `${OLLAMA_BASE_URL}/chat/completions`,
        {
            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                model: OLLAMA_MODEL,

                messages: [
                    {
                        role: "system",
                        content: `
You are a travel itinerary assistant.

Update the provided itinerary according to
the traveller's request.

Preserve information that does not need changing.

Return only valid JSON.
`
                    },

                    {
                        role: "user",
                        content: `
Current itinerary:

${JSON.stringify(currentItinerary)}

Traveller request:

${userRequest}
`
                    }
                ],

                temperature: 0.2
            })
        }
    );

    if (!response.ok) {
        throw new Error(
            `Ollama request failed: ${response.status}`
        );
    }

    const data = await response.json();

    return data.choices[0].message.content;
}


module.exports = {
    updateItineraryWithOllama
};


