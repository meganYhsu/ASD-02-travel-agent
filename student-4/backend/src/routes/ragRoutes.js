const express = require("express");

const router = express.Router();

const RAG_SERVICE_URL =
    process.env.RAG_SERVICE_URL ||
    "http://127.0.0.1:7001";

router.post("/ask", async (req, res) => {
    try {
        const question =
            typeof req.body?.question === "string"
                ? req.body.question.trim()
                : "";

        if (!question) {
            return res.status(400).json({
                success: false,
                error: "question is required"
            });
        }

        const response = await fetch(
            `${RAG_SERVICE_URL}/rag/retrieve`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    query: question,
                    k: 5
                })
            }
        );

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            return res.status(response.status || 502).json({
                success: false,
                error:
                    result.error ||
                    "Shared RAG request failed"
            });
        }

        return res.status(200).json({
            success: true,
            data: {
                answer:
                    result.results?.[0]?.text ||
                    "No matching RAG context found.",
                citations:
                    result.results?.map((item) => ({
                        chunk_id: item.chunk_id,
                        source_id: item.source_id,
                        authority_tier: item.authority_tier
                    })) || [],
                confidenceCategory:
                    result.results?.length > 0
                        ? "Retrieved"
                        : "Unknown",
                retrievalSummary: {
                    k: result.k,
                    retrieved_count:
                        result.results?.length || 0,
                    top_chunk:
                        result.results?.[0]?.chunk_id || null
                }
            }
        });

    } catch (error) {
        console.error("Shared RAG error:", error);

        return res.status(503).json({
            success: false,
            error: "Shared RAG service unavailable"
        });
    }
});

module.exports = router;
