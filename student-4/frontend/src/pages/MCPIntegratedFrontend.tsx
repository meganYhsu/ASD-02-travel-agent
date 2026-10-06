import React, { useState } from "react";
import { useLocation } from "react-router-dom";

type MCPToolResult = {
    toolName: string;
    payload: any;
    isError?: boolean;
};

function decodeHtml(value: string) {
    const parser = new DOMParser();
    return parser.parseFromString(value, "text/html").documentElement.textContent || value;
}

function parseMCPBackendResponse(toolName: string, responseText: string): MCPToolResult {
    const preMatch = responseText.match(/<pre>([\s\S]*?)<\/pre>/i);
    const jsonText = preMatch ? decodeHtml(preMatch[1]) : responseText;

    try {
        return {
            toolName,
            payload: JSON.parse(jsonText)
        };
    } catch {
        return {
            toolName,
            payload: jsonText
        };
    }
}

function formatLabel(key: string) {
    return key
        .replace(/_/g, " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function parseTravelRequirements(value: unknown) {
    if (typeof value !== "string") {
        return {
            destination: "Not provided",
            requirements: "Not provided"
        };
    }

    try {
        const parsed = JSON.parse(value);
        return {
            destination: parsed.destination || "Not provided",
            requirements: parsed.Requirements || parsed.requirements || "Not provided"
        };
    } catch {
        return {
            destination: "Not provided",
            requirements: value
        };
    }
}

function renderGenericValue(value: any): React.ReactNode {
    if (value === null || value === undefined || value === "") {
        return <span className="muted">Not provided</span>;
    }

    if (Array.isArray(value)) {
        if (value.length === 0) {
            return <span className="muted">No records returned</span>;
        }

        return (
            <ol className="option-card__list">
                {value.map((item, index) => (
                    <li key={index}>
                        {typeof item === "object" && item !== null
                            ? renderGenericObject(item)
                            : String(item)}
                    </li>
                ))}
            </ol>
        );
    }

    if (typeof value === "object") {
        return renderGenericObject(value);
    }

    return String(value);
}

function renderGenericObject(payload: Record<string, any>) {
    return (
        <div className="option-card__section">
            {Object.entries(payload).map(([key, value]) => (
                <section
                    key={key}
                    className="option-card"
                >
                    <strong
                        className="option-card__label"
                    >
                        {formatLabel(key)}
                    </strong>
                    <div className="option-card__summary">
                        {renderGenericValue(value)}
                    </div>
                </section>
            ))}
        </div>
    );
}

function ItineraryToolOutput({ payload }: { payload: any }) {
    const travelRequirements = parseTravelRequirements(
        payload?.requirements?.["Requirements to travel"]
    );

    const activities = Array.isArray(payload?.activities?.activity_description)
        ? payload.activities.activity_description
        : [];

    return (
        <div className="option-card__section">
            <section
                className="option-card"
            >
                <strong className="option-card__label">Destination</strong>
                <p className="option-card__summary">{travelRequirements.destination}</p>
            </section>

            <section
                className="option-card"
            >
                <strong className="option-card__label">Requirements</strong>
                <p className="option-card__summary">{travelRequirements.requirements}</p>
            </section>

            <section className="option-card">
                <strong className="option-card__label">Activities</strong>
                {activities.length === 0 ? (
                    <p className="muted">
                        No activities returned.
                    </p>
                ) : (
                    <ol className="option-card__list">
                        {activities.map((activity: string, index: number) => (
                            <li key={index}>
                                {activity}
                            </li>
                        ))}
                    </ol>
                )}
            </section>
        </div>
    );
}

function MCPOutput({ result }: { result: MCPToolResult | null }) {
    if (!result) {
        return <>Your MCP Generated output will be here.</>;
    }

    if (typeof result.payload !== "object" || result.payload === null) {
        return <>{String(result.payload)}</>;
    }

    if (result.toolName === "get-itinerary") {
        return <ItineraryToolOutput payload={result.payload} />;
    }

    return renderGenericObject(result.payload);
}

function MCPIntegratedFile() {
    const location = useLocation();
    const itineraryIdFromState = Number((location.state as any)?.itineraryId || "");
    const [result, setResult] = useState<MCPToolResult | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [activeTool, setActiveTool] = useState("");
    const [dayNo, setDayNo] = useState("1");
    const selectedItineraryId = Number.isInteger(itineraryIdFromState)
        ? itineraryIdFromState
        : null;

    async function showOutputFromRequest(toolName: string, request: () => Promise<Response>) {
        setActiveTool(toolName);
        setIsLoading(true);
        setResult({
            toolName,
            payload: `Running ${toolName}...`
        });

        try {
            const response = await request();
            const responseText = await response.text();

            if (!response.ok) {
                setResult({
                    toolName,
                    payload: responseText || `Unable to run ${toolName}.`,
                    isError: true
                });
                return;
            }

            setResult(
                responseText
                    ? parseMCPBackendResponse(toolName, responseText)
                    : {
                        toolName,
                        payload: "No output was returned by this MCP tool."
                    }
            );
        } catch (error) {
            setResult({
                toolName,
                payload: error instanceof Error ? error.message : `Unable to run ${toolName}.`,
                isError: true
            });
        } finally {
            setIsLoading(false);
        }
    }





// a function that wil fetch all the activities from the mcp_mode file:
    async function runingMCPTool(toolName: "get-itinerary" | "get-activity"){
        if (selectedItineraryId === null) {
            setResult({
                toolName,
                payload: "No itinerary was provided. Please open MCP Integration from a saved itinerary.",
                isError: true
            });
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
            setResult({
                toolName,
                payload: "No itinerary was provided. Please open MCP Integration from a saved itinerary.",
                isError: true
            });
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

                            <div
                                className={`mcp-output__box${result?.isError ? " saved-itinerary-page__state--error" : ""}`}
                                aria-live="polite"
                            >
                                <MCPOutput result={result} />
                            </div>
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}

export default MCPIntegratedFile;
