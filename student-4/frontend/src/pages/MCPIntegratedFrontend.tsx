import React, { useState } from "react";
import { useLocation } from "react-router-dom";

function MCPIntegratedFile() {
    const location = useLocation();
    const itineraryIdFromState = Number((location.state as any)?.itineraryId || "");
    const [result, setResult] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [activeTool, setActiveTool] = useState("");
    const [dayNo, setDayNo] = useState("1");
    const selectedItineraryId = Number.isInteger(itineraryIdFromState)
        ? itineraryIdFromState
        : null;

    async function showOutputFromRequest(toolName: string, request: () => Promise<Response>) {
        setActiveTool(toolName);
        setIsLoading(true);
        setResult(`Running ${toolName}...`);

        try {
            const response = await request();
            const result = await response.text();

            if (!response.ok) {
                setResult(result || `Unable to run ${toolName}.`);
                return;
            }

            setResult(result || "No output was returned by this MCP tool.");
        } catch (error) {
            setResult(error instanceof Error ? error.message : `Unable to run ${toolName}.`);
        } finally {
            setIsLoading(false);
        }
    }





// a function that wil fetch all the activities from the mcp_mode file:
    async function runingMCPTool(toolName: "get-itinerary" | "get-activity"){
        if (selectedItineraryId === null) {
            setResult("No itinerary was provided. Please open MCP Integration from a saved itinerary.");
            return;
        }

        // building the endpint here:
        const endpoint = toolName === "get-itinerary"?
            "http://localhost:5004/api/mcp/get-itinerary":
            "http://localhost:5004/api/mcp/get-activity";

        await showOutputFromRequest(toolName, () => fetch(endpoint , {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body: JSON.stringify({
                itinerary_id: selectedItineraryId
            })
        }));
    }

    async function runSpecificMCPTool(toolName: string, needsDayNo = false) {
        if (selectedItineraryId === null) {
            setResult("No itinerary was provided. Please open MCP Integration from a saved itinerary.");
            return;
        }

        const argumentsPayload: {
            itinerary_id: number;
            day_no?: number;
        } = {
            itinerary_id: selectedItineraryId
        };

        if (needsDayNo) {
            argumentsPayload.day_no = Number(dayNo);
        }

        await showOutputFromRequest(toolName, () => fetch("http://localhost:5004/api/mcp/tool", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                tool_name: toolName,
                arguments: argumentsPayload
            })
        }));
    }

    return (
        <div className="travel-page">
            <div className="travel-page__shell">
                <header className="travel-page__hero">
                    <p className="travel-page__eyebrow">Result viewer</p>
                    <h1 className="travel-page__title">Itinerary result viewer</h1>
                    <p className="travel-page__intro">
                        View the generated result after running the required action.
                    </p>
                </header>



                <main>
                    <section className="travel-panel mcp-panel">
                        <div className="mcp-panel__controls">
                            <label className="mcp-panel__field">
                                <span>Day no</span>
                                <input
                                    type="number"
                                    min="1"
                                    value={dayNo}
                                    onChange={(event) => setDayNo(event.target.value)}
                                />
                            </label>

                            <nav className="mcp-toolbar" aria-label="MCP tools">
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runingMCPTool("get-itinerary")}
                                    disabled={isLoading}
                                >
                                    get-itinerary
                                </button>
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runingMCPTool("get-activity")}
                                    disabled={isLoading}
                                >
                                    get-activity
                                </button>
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runSpecificMCPTool("total_activity_count")}
                                    disabled={isLoading}
                                >
                                    total_activity_count
                                </button>

                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runSpecificMCPTool("get_activity_start_times")}
                                    disabled={isLoading}
                                >
                                    get_activity_start_times
                                </button>
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runSpecificMCPTool("get_travel_requirements")}
                                    disabled={isLoading}
                                >
                                    get_travel_requirements
                                </button>
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runSpecificMCPTool("total_activities_count_a_day", true)}
                                    disabled={isLoading}
                                >
                                    total_activities_count_a_day
                                </button>
                                <button
                                    className="travel-button"
                                    type="button"
                                    onClick={() => runSpecificMCPTool("get_trip_activities_for_day_desc", true)}
                                    disabled={isLoading}
                                >
                                    get_trip_activities_for_day_desc
                                </button>
                            </nav>

                        </div>

                        <div className="mcp-output">
                            <div className="mcp-output__head">
                                <div>
                                    <p className="mcp-output__eyebrow">Tool output</p>
                                    <h2>Generated MCP response</h2>
                                </div>
                                <span className="mcp-output__status">
                                    {isLoading ? "Running" : activeTool || "Ready"}
                                </span>
                            </div>

                            <pre className="mcp-output__box" aria-live="polite">
                                {result || "Your MCP Generated output will be here."}
                            </pre>
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}

export default MCPIntegratedFile;
