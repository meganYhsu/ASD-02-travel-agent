const Groq = require("groq-sdk");

let groq = null;

function getGroqClient() {
    const apiKey = process.env.GROQ_API_KEY;

    if (!apiKey) {
        return null;
    }

    if (!groq) {
        groq = new Groq({
            apiKey
        });
    }

    return groq;
}

module.exports = {
    getGroqClient
};