const Groq = require("groq-sdk");
const fs = require("fs");
const path = require("path");

const groq = new Groq({
    apiKey: process.env.GROQ_API_KEY
});

const cityListPrompt = fs.readFileSync(
    path.resolve(__dirname, "../../prompts/generate_city_list"),
    "utf8"
);

function generateCityList(destination, template) {
    return template.replace("${destination}", destination);
}

async function generateCitiesList(req, res) {
    try {
        const { destination } = req.body;

        if (!destination) {
            return res.status(400).json({
                error: "Destination is required"
            });
        }

        const prompt = generateCityList(
            destination,
            cityListPrompt
        );

        const response = await groq.chat.completions.create({
            messages: [
                {
                    role: "user",
                    content: prompt
                }
            ],
            model: process.env.GROQ_MODEL
        });

        const aiResponse =
            response.choices[0].message.content;

        const cities = JSON.parse(aiResponse);

        return res.json(cities);

    } catch (error) {
        console.error(error);

        return res.status(500).json({
            error: "Could not generate cities"
        });
    }
}

module.exports = {
    generateCitiesList
};
