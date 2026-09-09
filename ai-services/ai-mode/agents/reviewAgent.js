const fs = require("fs");
const path = require("path");

const PROMPT_DIR =
    path.resolve(__dirname, "../prompts");

const DEFAULT_BASE_URL =
    "http://localhost:11434/v1";


function loadPrompt(relativePath) {

    const filePath =
        path.join(
            PROMPT_DIR,
            relativePath
        );

    if (!fs.existsSync(filePath)) {

        throw new Error(
            `Prompt file not found: ${filePath}`
        );
    }


    return fs
        .readFileSync(filePath, "utf8")
        .trim();
}


function evidenceToText(evidence) {

    if (typeof evidence === "string") {
        return evidence;
    }


    return JSON.stringify(
        evidence,
        null,
        2
    );
}


async function callModel({
                             baseUrl,
                             apiKey,
                             modelName,
                             systemPrompt,
                             userPrompt,
                             maxTokens = 600,
                             temperature = 0
                         }) {

    const trimmedBaseUrl =
        String(
            baseUrl ||
            DEFAULT_BASE_URL
        ).replace(/\/$/, "");


    const response =
        await fetch(
            `${trimmedBaseUrl}/chat/completions`,
            {
                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    ...(apiKey
                        ? {
                            Authorization:
                                `Bearer ${apiKey}`
                        }
                        : {})
                },

                body: JSON.stringify({
                    model: modelName,

                    messages: [
                        {
                            role: "system",
                            content: systemPrompt
                        },
                        {
                            role: "user",
                            content: userPrompt
                        }
                    ],

                    max_tokens:
                    maxTokens,

                    temperature
                }),

                signal:
                    AbortSignal.timeout(
                        120000
                    )
            }
        );


    if (!response.ok) {

        throw new Error(
            `HTTP ${response.status}: ${
                await response.text()
            }`
        );
    }


    const payload =
        await response.json();


    const content =
        payload
            ?.choices
            ?.[0]
            ?.message
            ?.content;


    return content &&
    content.trim()
        ? content.trim()
        : "";
}


async function getReview({
                             student,
                             task,
                             implementationRecommendation,
                             validationEvidence,
                             carryForward = "",
                             modelConfig = {}
                         }) {

    try {

        if (
            !/^student-[1-5]$/.test(
                student
            )
        ) {
            throw new Error(
                `Invalid student identifier: ${student}`
            );
        }


        const systemPrompt =
            loadPrompt(
                path.join(
                    "Shared",
                    "review_system_prompt.txt"
                )
            );


        const taskPromptTemplate =
            loadPrompt(
                path.join(
                    student,
                    "review_task.txt"
                )
            );


        const taskPrompt =
            taskPromptTemplate

                .replaceAll(
                    "{{STUDENT}}",
                    student
                )

                .replaceAll(
                    "{{TASK}}",
                    task
                )

                .replaceAll(
                    "{{IMPLEMENTATION_RECOMMENDATION}}",
                    implementationRecommendation
                )

                .replaceAll(
                    "{{VALIDATION_EVIDENCE}}",
                    evidenceToText(
                        validationEvidence
                    )
                )

                .replaceAll(
                    "{{CARRY_FORWARD}}",
                    carryForward ||
                    "none"
                );


        const content =
            await callModel({

                baseUrl:
                    modelConfig.baseUrl ||
                    process.env
                        .REVIEW_BASE_URL ||
                    process.env
                        .OLLAMA_BASE_URL ||
                    DEFAULT_BASE_URL,

                apiKey:
                    modelConfig.apiKey ||
                    process.env
                        .OLLAMA_API_KEY ||
                    "",

                modelName:
                    modelConfig.modelName ||
                    process.env
                        .REVIEW_MODEL ||
                    process.env
                        .OLLAMA_REVIEW_MODEL ||
                    "qwen2.5:3b",

                systemPrompt,

                userPrompt:
                taskPrompt
            });


        return {
            content,

            error:
                content
                    ? ""
                    : "Review agent returned an empty response."
        };


    } catch (error) {

        return {
            content: "",

            error:
                error instanceof Error
                    ? error.message
                    : String(error)
        };
    }
}


module.exports = {
    getReview
};

