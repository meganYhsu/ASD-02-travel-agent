const express = require("express");

const router = express.Router();

const MCP_BASE_URL =
    process.env.MCP_BASE_URL || "http://localhost:7004";

function MCPRenderJSON(title, payload) {
    return `
        <h3>${title}</h3>
        <pre>${JSON.stringify(payload, null, 2)}</pre>
    `;
}

async function callPythonMCPTool(toolName, args) {
    const response = await fetch(`${MCP_BASE_URL}/mcp/tool`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            tool_name: toolName,
            arguments: args
        })
    });

    const payload = await response.json();

    if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "MCP tool call failed");
    }

    return payload.result;
}

router.post("/mcp/get-itinerary", async (req, res) => {
    const itineraryId = Number(req.body.itinerary_id);

    if (!Number.isInteger(itineraryId)) {
        return res.status(400).send("<p>itinerary_id is required.</p>");
    }

    try {
        const args = {
            itinerary_id: itineraryId
        };

        const [
            totalActivities,
            requirements,
            startTimes,
            activities
        ] = await Promise.all([
            callPythonMCPTool("total_activity_count", args),
            callPythonMCPTool("get_travel_requirements", args),
            callPythonMCPTool("get_activity_start_times", args),
            callPythonMCPTool("get_trip_activities_desc", args)
        ]);

        return res
            .status(200)
            .send(MCPRenderJSON("MCP Tool: get_itinerary", {
                itinerary_id: itineraryId,
                totalActivities,
                requirements,
                startTimes,
                activities
            }));
    } catch (error) {
        return res.status(503).send(`
            <p>MCP get_itinerary failed.</p>
            <pre>${error.message}</pre>
        `);
    }
});

router.post("/mcp/get-activity", async (req, res) => {
    const itineraryId = Number(req.body.itinerary_id);

    if (!Number.isInteger(itineraryId)) {
        return res.status(400).send("<p>itinerary_id is required.</p>");
    }

    try {
        const activities = await callPythonMCPTool(
            "get_trip_activities_desc",
            {
                itinerary_id: itineraryId
            }
        );

        return res
            .status(200)
            .send(MCPRenderJSON("MCP Tool: get_activities", activities));
    } catch (error) {
        return res.status(503).send(`
            <p>MCP get_activity failed.</p>
            <pre>${error.message}</pre>
        `);
    }
});

router.post("/mcp/tool", async (req, res) => {
    const {
        tool_name: toolName,
        arguments: toolArguments
    } = req.body;

    if (!toolName) {
        return res.status(400).send("<p>tool_name is required.</p>");
    }

    try {
        const result = await callPythonMCPTool(
            toolName,
            toolArguments || {}
        );

        return res
            .status(200)
            .send(MCPRenderJSON(`MCP Tool: ${toolName}`, result));
    } catch (error) {
        return res.status(503).send(`
            <p>MCP tool failed.</p>
            <pre>${error.message}</pre>
        `);
    }
});

module.exports = router;
