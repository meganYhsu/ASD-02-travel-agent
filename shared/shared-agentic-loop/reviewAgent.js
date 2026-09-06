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
    const trimmedBaseUrl = String(baseUrl || DEFAULT_BASE_URL).replace(/\/$/, "");

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
            temperature: 0,
            max_tokens: 300
        })
    }
    );

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const data = await response.json();

    return data?.choices?.[0]?.message?.content?.trim() || "";
}


async function getReview({
    task,
    implementationRecommendation,
    evidence,
    promptDir,
    modelConfig = {}
}) {

    const systemPrompt = loadPrompt(
        promptDir,
        "review_system_prompt.txt",
        "You are the review agent for the Travel-Agent project."
    );

    const taskTemplate = loadPrompt(
        promptDir,
        "review_task_prompt.txt",
        `Task: {{TASK}} 
        Implementation Agent recommendation: {{IMPLEMENTATION_RECOMMENDATION}} 
        Evidence: {{EVIDENCE}}
        Review the recommendation against the evidence. 
        Identify whether the recommendation is supported,practical, and appropriate.
        `
    );

    const userPrompt = taskTemplate
        .replaceAll("{{TASK}}", task)
        .replaceAll("{{IMPLEMENTATION_RECOMMENDATION}}", implementationRecommendation
        )
        .replaceAll("{{EVIDENCE}}", evidence);

    const content = await callModel({
        baseUrl: modelConfig.baseUrl || process.env.OLLAMA_BASE_URL || DEFAULT_BASE_URL,

        modelName: modelConfig.modelName || process.env.OLLAMA_REVIEW_MODEL || process.env.OLLAMA_MODEL || "qwen2.5:0.5b",
        systemPrompt,
        userPrompt
    });

    return {
        content,
        error: content ? "" : "Review agent returned an empty response."
    };
}

module.exports = {
    getReview
};