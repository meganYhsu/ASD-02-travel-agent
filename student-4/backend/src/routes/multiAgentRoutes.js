const express = require("express");
const {
    getItinerary,
    DatabaseUnavailableError,
    DatabaseRequestError
} = require("../services/DBService");

const router = express.Router();
const MULTI_AGENT_SERVICE_URL = (
    process.env.MULTI_AGENT_SERVICE_URL || "http://127.0.0.1:6767"
).replace(/\/$/, "");
const REVIEW_DECISIONS = new Set(["Accept", "Partially Accept", "Reject"]);

class MultiAgentRequestError extends Error {
    constructor(status, message) {
        super(message);
        this.status = status;
    }
}

async function requestMultiAgent(path, method = "GET", body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 720000);

    try {
        const response = await fetch(`${MULTI_AGENT_SERVICE_URL}${path}`, {
            method,
            headers: { "Content-Type": "application/json" },
            signal: controller.signal,
            ...(body === undefined ? {} : { body: JSON.stringify(body) })
        });
        let result;

        try {
            result = await response.json();
        } catch {
            throw new MultiAgentRequestError(502, "Multi-agent service returned an invalid response");
        }

        if (!response.ok || result?.status === "error") {
            throw new MultiAgentRequestError(
                response.ok ? 502 : response.status,
                result?.error || "Multi-agent request failed"
            );
        }

        if (!result || typeof result !== "object" || Array.isArray(result)) {
            throw new MultiAgentRequestError(502, "Multi-agent service returned an invalid response");
        }

        return result;
    } catch (error) {
        if (error instanceof MultiAgentRequestError) throw error;
        throw new MultiAgentRequestError(
            error.name === "AbortError" ? 504 : 503,
            error.name === "AbortError" ? "Multi-agent request timed out" : "Multi-agent service unavailable"
        );
    } finally {
        clearTimeout(timeout);
    }
}

function sendError(res, error) {
    if (error instanceof DatabaseUnavailableError) {
        return res.status(503).json({ success: false, error: "Database service unavailable" });
    }
    if (error instanceof DatabaseRequestError) {
        return res.status(error.status === 404 ? 404 : 502).json({
            success: false,
            error: error.status === 404 ? "Saved itinerary not found" : "Could not retrieve saved itinerary"
        });
    }
    if (error instanceof MultiAgentRequestError) {
        return res.status(error.status).json({ success: false, error: error.message });
    }
    console.error("Multi-agent integration error:", error);
    return res.status(500).json({ success: false, error: "Multi-agent request failed" });
}

router.post("/workflow", async (req, res) => {
    const { itineraryId, userRequest } = req.body || {};
    if (!Number.isSafeInteger(itineraryId) || itineraryId <= 0) {
        return res.status(400).json({ success: false, error: "A positive integer itineraryId is required" });
    }
    if (typeof userRequest !== "string" || !userRequest.trim()) {
        return res.status(400).json({ success: false, error: "userRequest is required" });
    }

    try {
        const response = await getItinerary(itineraryId);
        const saved = response.data || response;
        if (!saved.itinerary) {
            return res.status(404).json({ success: false, error: "Saved itinerary not found" });
        }

        const result = await requestMultiAgent("/workflow", "POST", {
            user_request: userRequest.trim(),
            itinerary_context: {
                itinerary: saved.itinerary,
                activities: Array.isArray(saved.activities) ? saved.activities : []
            }
        });
        return res.status(200).json({ success: true, data: result });
    } catch (error) {
        return sendError(res, error);
    }
});

router.get("/workflows/:id", async (req, res) => {
    try {
        const result = await requestMultiAgent(`/workflow/${encodeURIComponent(req.params.id)}`);
        return res.status(200).json({ success: true, data: result });
    } catch (error) {
        return sendError(res, error);
    }
});

router.post("/workflows/:id/review", async (req, res) => {
    const { decision, reason, evidence = "" } = req.body || {};
    if (!REVIEW_DECISIONS.has(decision)) {
        return res.status(400).json({ success: false, error: "decision must be Accept, Partially Accept, or Reject" });
    }
    if (typeof reason !== "string" || reason.trim().length < 20) {
        return res.status(400).json({ success: false, error: "reason must contain at least 20 characters" });
    }
    if (typeof evidence !== "string") {
        return res.status(400).json({ success: false, error: "evidence must be a string" });
    }

    try {
        const result = await requestMultiAgent(`/workflow/${encodeURIComponent(req.params.id)}/review`, "POST", {
            decision,
            reason: reason.trim(),
            evidence: evidence.trim()
        });
        return res.status(200).json({ success: true, data: result });
    } catch (error) {
        return sendError(res, error);
    }
});

module.exports = router;
