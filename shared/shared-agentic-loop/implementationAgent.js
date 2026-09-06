const fs = require("fs");
const path = require("path");

const DEFAULT_BASE_URL = "http://localhost:11434/v1";

function loadPrompt(promptDir, filename, fallback) {
    try {
        return fs.readFileSync(
            path.join(promptDir, filename),
            "utf8"
        ).trim();
    } catch {
        return fallback.trim();
    }
}

async function callModel({
    baseUrl,
    modelName,
    systemPrompt,
    userPrompt
}) {
    const trimmedBaseUrl =
        String(baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");

    const response = await fetch(`${trimmedBaseUrl}/chat/completions`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            model: modelName,
            messages: [
                { role: "system", content: systemPrompt },
                { role: "user", content: userPrompt }
            ],
            temperature: 0.1,
            max_tokens: 300
        })
    }
    );

    if (!response.ok) {
        throw new Error(
            `HTTP ${response.status}: ${await response.text()}`
        );
    }

    const data = await response.json();

    return data?.choices?.[0]?.message?.content?.trim() || "";
}


async function getImplementationAdvice({
    task,
    evidence,
    promptDir,
    carryForward = "",
    modelConfig = {}
}) {

    const systemPrompt = loadPrompt(
        promptDir,
        "implementation_system_prompt.txt",
        "You are an implementation reviewer for the Travel-Agent project."
    );

    const taskTemplate = loadPrompt(
        promptDir,
        "implementation_task_prompt.txt",
        `Task: {{TASK}}
        Evidence: {{EVIDENCE}}
        Previous human/reviewer feedback: {{CARRY_FORWARD}}
        Identify verified implementation problems and recommend minimal practical improvements.`
    );

    const userPrompt = taskTemplate
        .replaceAll("{{TASK}}", task)
        .replaceAll("{{EVIDENCE}}", evidence)
        .replaceAll(
            "{{CARRY_FORWARD}}",
            carryForward || "None"
        );

    const content = await callModel({
        baseUrl: modelConfig.baseUrl || process.env.OLLAMA_BASE_URL || DEFAULT_BASE_URL,

        modelName: modelConfig.modelName || process.env.OLLAMA_MODEL || "qwen2.5:0.5b",
        systemPrompt,
        userPrompt
    });

    return {
        content,
        error: content ? "" : "Implementation agent returned an empty response."
    };
}

module.exports = {
    getImplementationAdvice
};