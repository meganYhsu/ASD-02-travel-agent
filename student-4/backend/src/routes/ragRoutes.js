const express = require("express");

const router = express.Router();

const RAG_SERVICE_URL =
    process.env.RAG_SERVICE_URL ||
    "http://127.0.0.1:7001";

router.post("/rag/ask", async (req, res) => {
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

    try {
        const response = await fetch(`${RAG_SERVICE_URL}/rag/answer`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: question,
                k: 5
            })
        });

        const result = await response.json();

        if (!response.ok || result.status !== "success") {
            return res.status(response.status || 502).json({
                success: false,
                error: result.error || "Shared RAG request failed"
            });
        }

        return res.status(200).json({
            success: true,
            data: {
                answer: result.answer || "Insufficient evidence.",
                citations:
                    result.citations?.map((item) => ({
                        chunk_id: item.chunk_id,
                        source_id: item.source_id,
                        authority_tier: item.authority_tier
                    })) || [],
                confidenceCategory:
                    result.confidence_category || "Unknown",
                retrievalSummary: {
                    k: result.retrieval_summary?.k || 5,
                    retrieved_count:
                        result.retrieval_summary?.retrieved_count || 0,
                    top_chunk:
                        result.retrieval_summary?.top_chunk || null
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