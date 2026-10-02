import React, { useState } from "react";
import { useLocation } from "react-router-dom";

function MCPIntegratedFile() {
    const location = useLocation();
    const itineraryIdFromState = Number((location.state as any)?.itineraryId || "");
    const [result, setResult] = useState("");
    const [dayNo, setDayNo] = useState("1");
    const selectedItineraryId = Number.isInteger(itineraryIdFromState)
        ? itineraryIdFromState
        : null;






    function showResult() {
        setResult("Result will be generated here.");
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

        const response = await fetch(endpoint , {
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body: JSON.stringify({
                itinerary_id: selectedItineraryId
            })
        });
        const result = await response.text();
        setResult(result);
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

        const response = await fetch("http://localhost:5004/api/mcp/tool", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                tool_name: toolName,
                arguments: argumentsPayload
            })
        });

        const result = await response.text();
        setResult(result);
    }

    return (
        <div className="travel-page">
            <div className="travel-page__shell">
                <nav
                    className="mcp-toolbar"
                    style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "24px",
                        marginBottom: "28px"
                    }}
                >
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runingMCPTool("get-itinerary")}
                    >
                        get-itinerary
                    </button>
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runingMCPTool("get-activity")}
                    >
                        get-activity
                    </button>
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runSpecificMCPTool("total_activity_count")}
                    >
                        total_activity_count
                    </button>

                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runSpecificMCPTool("get_activity_start_times")}
                    >
                        get_activity_start_times
                    </button>
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runSpecificMCPTool("get_travel_requirements")}
                    >
                        get_travel_requirements
                    </button>
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runSpecificMCPTool("total_activities_count_a_day", true)}
                    >
                        total_activities_count_a_day
                    </button>
                    <button
                        className="travel-button"
                        type="button"
                        onClick={() => runSpecificMCPTool("get_trip_activities_for_day_desc", true)}
                    >
                        get_trip_activities_for_day_desc
                    </button>
                </nav>

                <header className="travel-page__hero">
                    <p className="travel-page__eyebrow">Result viewer</p>
                    <h1 className="travel-page__title">Itinerary result viewer</h1>
                    <p className="travel-page__intro">
                        View the generated result after running the required action.
                    </p>
                </header>



                <main>
                    <section
                        className="travel-panel mcp-result-panel"
                        style={{
                            display: "grid",
                            gap: "18px",
                            maxWidth: "100%",
                            overflow: "hidden",
                            borderRadius: "20px",
                            padding: "22px",
                            background: "rgba(255, 255, 255, 0.84)",
                            border: "1px solid rgba(24, 53, 68, 0.12)",
                            boxShadow: "0 18px 42px rgba(18, 38, 49, 0.08)"
                        }}
                    >
                        <div
                            className="mcp-result-panel__head"
                            style={{
                                display: "flex",
                                flexWrap: "wrap",
                                alignItems: "end",
                                justifyContent: "space-between",
                                gap: "16px",
                                minWidth: 0
                            }}
                        >
                            <label
                                className="mcp-day-field"
                                style={{
                                    display: "grid",
                                    gap: "8px",
                                    fontWeight: 700
                                }}
                            >
                                Day no
                                <input
                                    type="number"
                                    min="1"
                                    value={dayNo}
                                    onChange={(event) => setDayNo(event.target.value)}
                                    style={{
                                        width: "120px",
                                        minHeight: "44px",
                                        border: "1px solid rgba(28, 59, 76, 0.18)",
                                        borderRadius: "12px",
                                        padding: "10px 12px"
                                    }}
                                />
                            </label>

                            <div>
                                <h2 style={{ margin: 0 }}>Tool's generated output</h2>
                            </div>

                        </div>

                        <pre
                            className="mcp-output"
                            style={{
                                width: "100%",
                                maxWidth: "100%",
                                maxHeight: "560px",
                                margin: 0,
                                overflow: "auto",
                                whiteSpace: "pre-wrap",
                                overflowWrap: "anywhere",
                                wordBreak: "break-word",
                                boxSizing: "border-box",
                                border: "1px solid rgba(28, 59, 76, 0.1)",
                                borderRadius: "16px",
                                padding: "18px",
                                background: "rgba(250, 252, 253, 0.96)",
                                color: "#183042",
                                fontSize: "0.92rem",
                                lineHeight: 1.55
                            }}
                        >
                            {result || "Output"}
                        </pre>
                    </section>
                </main>
            </div>
        </div>
    );
}

export default MCPIntegratedFile;
