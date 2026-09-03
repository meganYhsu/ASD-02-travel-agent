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
    maxTokens = 220,
    temperature = 0.1
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

async function getImplementationAdvice({
    task,
    validationEvidence,
    carryForward = "",
    modelConfig = {}
}) {
    try {
        const systemPrompt = loadPrompt(
            "implementation_system_prompt.txt",
            "You are the implementation agent for the travel-agent project."
        );
        const taskPrompt = loadPrompt(
            "implementation_task_prompt.txt",
            [
                "Task:",
                "{{TASK}}",
                "",
                "Validation evidence:",
                "{{VALIDATION_EVIDENCE}}",
                "",
                "Human or reviewer carry-forward notes:",
                "{{CARRY_FORWARD}}"
            ].join("\n")
        )
            .replaceAll("{{TASK}}", task)
            .replaceAll("{{VALIDATION_EVIDENCE}}", validationEvidence)
            .replaceAll("{{CARRY_FORWARD}}", carryForward || "none");

        const content = await callModel({
            baseUrl: modelConfig.baseUrl || process.env.LLAMA_BASE_URL || process.env.OLLAMA_BASE_URL || DEFAULT_BASE_URL,
            apiKey: modelConfig.apiKey || process.env.LLAMA_API_KEY || process.env.OLLAMA_API_KEY || "",
            modelName: modelConfig.modelName || process.env.OLLAMA_MODEL || process.env.LLAMA_MODEL || "llama3.1",
            systemPrompt,
            userPrompt: taskPrompt
        });

        return {
            content,
            error: content ? "" : "Implementation agent returned an empty response."
        };
    } catch (error) {
        return {
            content: "",
            error: error.message
        };
    }
}

module.exports = {
    getImplementationAdvice
};
