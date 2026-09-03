const fs = require("fs");
const path = require("path");

const PROMPT_DIR = path.resolve(__dirname, "../../prompts");
const DEFAULT_BASE_URL = "http://localhost:11434/v1";

function loadPrompt(filename, fallback) {
    try {
        return fs.readFileSync(path.join(PROMPT_DIR, filename), "utf8").trim();
    } catch {
        return fallback.trim();
    }
}

async function callModel({
    baseUrl,
    apiKey,
    modelName,
    systemPrompt,
    userPrompt,
    maxTokens = 240,
    temperature = 0
}) {
    const trimmedBaseUrl = String(baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");
    const response = await fetch(`${trimmedBaseUrl}/chat/completions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {})
        },
        body: JSON.stringify({
            model: modelName,
            messages: [
                { role: "system", content: systemPrompt },
                { role: "user", content: userPrompt }
            ],
            max_tokens: maxTokens,
            temperature
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const payload = await response.json();
    const content = payload?.choices?.[0]?.message?.content;
    return content && content.trim() ? content.trim() : "";
}

async function getReview({
    task,
    implementationRecommendation,
    validationEvidence,
    modelConfig = {}
}) {
    try {
        const systemPrompt = loadPrompt(
            "review_system_prompt.txt",
            "You are the reviewer for the travel-agent project."
        );
        const taskPrompt = loadPrompt(
            "review_task_prompt.txt",
            [
                "Task:",
                "{{TASK}}",
                "",
                "Implementation recommendation:",
                "{{IMPLEMENTATION_RECOMMENDATION}}",
                "",
                "Validation evidence:",
                "{{VALIDATION_EVIDENCE}}"
            ].join("\n")
        )
            .replaceAll("{{TASK}}", task)
            .replaceAll("{{IMPLEMENTATION_RECOMMENDATION}}", implementationRecommendation)
            .replaceAll("{{VALIDATION_EVIDENCE}}", validationEvidence);

        const content = await callModel({
            baseUrl: modelConfig.baseUrl || process.env.QWEN_BASE_URL || process.env.OLLAMA_BASE_URL || DEFAULT_BASE_URL,
            apiKey: modelConfig.apiKey || process.env.QWEN_API_KEY || process.env.OLLAMA_API_KEY || "",
            modelName: modelConfig.modelName || process.env.OLLAMA_REVIEW_MODEL || process.env.QWEN_MODEL || "qwen2.5",
            systemPrompt,
            userPrompt: taskPrompt
        });

        return {
            content,
            error: content ? "" : "Review agent returned an empty response."
        };
    } catch (error) {
        return {
            content: "",
            error: error.message
        };
    }
}

module.exports = {
    getReview
};
