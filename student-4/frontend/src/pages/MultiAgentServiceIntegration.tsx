import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";

const reviewOptions = [
    { value: "Accept", label: "Accept", description: "Looks good to me." },
    { value: "Partially Accept", label: "Partially accept", description: "Good start, with some changes." },
    { value: "Reject", label: "Reject", description: "Let's take another approach." }
] as const;

type ReviewDecision = typeof reviewOptions[number]["value"];

type AgentResult = {
    status?: string;
    model?: string;
    plan?: string;
    output?: string;
    review?: string;
    error?: string;
};

type WorkflowResult = {
    workflow_id: string;
    itinerary_id: number;
    status: string;
    planner_result: AgentResult;
    worker_result: AgentResult;
    reviewer_result: AgentResult;
    human_decision: {
        status: string;
        decision?: ReviewDecision;
        reason?: string;
        evidence?: string;
    };
};

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:5004").replace(/\/$/, "");

async function requestWorkflow(path: string, signal: AbortSignal, body?: object): Promise<WorkflowResult> {
    let response;
    try {
        response = await fetch(`${API_BASE_URL}/api/multi-agent${path}`, {
            method: body ? "POST" : "GET",
            signal,
            ...(body ? {
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            } : {})
        });
    } catch (error) {
        if (signal.aborted) throw error;
        throw new Error("Unable to reach the travel backend. Check that it is running and try again.");
    }

    let payload;
    try {
        payload = await response.json();
    } catch {
        throw new Error(`The backend returned an invalid response (HTTP ${response.status}).`);
    }
    if (!response.ok || payload?.success !== true) {
        throw new Error(typeof payload?.error === "string" ? payload.error : `Request failed (HTTP ${response.status}).`);
    }

    const result = payload.data;
    if (
        typeof result?.workflow_id !== "string" || !result.workflow_id
        || !Number.isSafeInteger(result.itinerary_id)
        || typeof result.status !== "string"
        || ![result.planner_result, result.worker_result, result.reviewer_result, result.human_decision]
            .every((value) => value !== null && typeof value === "object" && !Array.isArray(value))
    ) {
        throw new Error("The backend returned an incomplete workflow response.");
    }
    return result;
}

function AgentOutput({ title, result }: { title: string; result: AgentResult }) {
    return (
        <section>
            <h3>{title}</h3>
            <p>Status: {result.status || "Unknown"}{result.model ? ` · Model: ${result.model}` : ""}</p>
            <pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{result.plan || result.output || result.review || result.error || "No agent output returned."}</pre>
            {result.error && <p role="alert">{result.error}</p>}
        </section>
    );
}

function MultiAgentServiceIntegration() {
    const location = useLocation();
    const pageState = location.state as { itineraryId?: number } | null;
    const itineraryId = Number.isSafeInteger(pageState?.itineraryId) && Number(pageState?.itineraryId) > 0
        ? pageState?.itineraryId
        : null;
    const [request, setRequest] = useState("");
    const [workflow, setWorkflow] = useState<WorkflowResult | null>(null);
    const [decision, setDecision] = useState<ReviewDecision | "">("");
    const [feedback, setFeedback] = useState("");
    const [evidence, setEvidence] = useState("");
    const [reasonError, setReasonError] = useState("");
    const [showWorkflowStatus, setShowWorkflowStatus] = useState(false);
    const [confirmation, setConfirmation] = useState("");
    const [error, setError] = useState("");
    const [activeAction, setActiveAction] = useState<"generate" | "status" | "review" | null>(null);
    const activeRequest = useRef<AbortController | null>(null);

    useEffect(() => () => activeRequest.current?.abort(), []);

    const savedReview = workflow?.human_decision.status === "recorded" ? workflow.human_decision : null;
    const busy = activeAction !== null;
    const hasAgentFailures = workflow && [workflow.planner_result, workflow.worker_result, workflow.reviewer_result]
        .some((result) => result.status !== "success" || Boolean(result.error));

    const workflowStatus = activeAction === "generate"
        ? "Running agents — waiting for the service response"
        : !workflow
        ? "Ready for a request"
        : !savedReview
            ? hasAgentFailures ? "Agent execution incomplete — human review pending" : "Awaiting human review"
            : savedReview.decision === "Accept"
                ? "Accepted"
                : savedReview.decision === "Partially Accept"
                    ? "Partially accepted — changes requested"
                    : "Rejected — revision needed";

    async function runRequest(action: "generate" | "status" | "review", path: string, body?: object) {
        if (activeRequest.current) return;
        const controller = new AbortController();
        activeRequest.current = controller;
        setActiveAction(action);
        setError("");
        setConfirmation("");
        try {
            const result = await requestWorkflow(path, controller.signal, body);
            if (result.itinerary_id !== itineraryId) throw new Error("The workflow does not belong to the selected itinerary.");
            if (action !== "generate" && result.workflow_id !== workflow?.workflow_id) {
                throw new Error("The backend returned a different workflow.");
            }
            if (action === "review" && result.human_decision.status !== "recorded") {
                throw new Error("The service did not confirm that your review was recorded. Check workflow status before trying again.");
            }
            if (controller.signal.aborted) return;
            setWorkflow(result);
            setShowWorkflowStatus(true);
            if (action === "review") setConfirmation("Your decision, reason, and evidence have been saved by the service.");
        } catch (failure) {
            if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "The workflow request failed.");
        } finally {
            if (activeRequest.current === controller) {
                activeRequest.current = null;
                setActiveAction(null);
            }
        }
    }

    function generateOutput(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!request.trim() || !itineraryId || activeRequest.current) return;

        setWorkflow(null);
        setDecision("");
        setFeedback("");
        setEvidence("");
        setReasonError("");
        setShowWorkflowStatus(true);
        void runRequest("generate", "/workflow", { itineraryId, userRequest: request.trim() });
    }

    function submitFeedback(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!workflow || !decision || activeRequest.current) return;
        if (feedback.trim().length < 20) {
            setReasonError("Please explain your decision in at least 20 characters, including what worked or needs to change.");
            return;
        }

        setReasonError("");
        void runRequest("review", `/workflows/${encodeURIComponent(workflow.workflow_id)}/review`, {
            decision,
            reason: feedback.trim(),
            evidence: evidence.trim()
        });
    }

    return (
        <main className="multi-agent-page">
            <div className="multi-agent-page__shell">
                <nav className="multi-agent-page__nav" aria-label="Page navigation">
                    <Link to="/">← Back to travel planner</Link>
                    <span className="multi-agent-page__badge">Multi-agent workflow</span>
                </nav>

                <header className="multi-agent-page__hero">
                    <p className="multi-agent-page__eyebrow">Multi-agent travel assistant</p>
                    <h1>A little input. A world of possibilities.</h1>
                    <p>Tell us what you have in mind, explore the response, and help shape what comes next.</p>
                    <p>{itineraryId ? `Selected saved itinerary: #${itineraryId}` : "Open this page from a saved itinerary to select a travel plan."}</p>
                </header>

                {error && <p role="alert">{error}</p>}

                <div className="multi-agent-page__workspace">
                    <section className="multi-agent-page__card" aria-labelledby="request-heading">
                        <div className="multi-agent-page__section-heading">
                            <span className="multi-agent-page__step" aria-hidden="true">01</span>
                            <div>
                                <h2 id="request-heading">Start with your idea</h2>
                                <p>Your next trip starts here.</p>
                            </div>
                        </div>
                        <form onSubmit={generateOutput}>
                            <label htmlFor="travel-request">What would you like help with?</label>
                            <textarea
                                id="travel-request"
                                value={request}
                                onChange={(event) => setRequest(event.target.value)}
                                placeholder="Plan a relaxed 5-day trip to Kyoto for two, with local food, temples, and a budget of $2,000."
                                rows={8}
                                required
                                disabled={busy || !itineraryId}
                                aria-describedby="request-hint"
                            />
                            <p id="request-hint" className="multi-agent-page__hint">Try including a destination, dates, budget, and things you enjoy.</p>
                            <button type="submit" disabled={busy || !itineraryId || !request.trim()}>{activeAction === "generate" ? "Generating…" : "Generate output"} <span aria-hidden="true">↗</span></button>
                        </form>
                    </section>

                    <section className="multi-agent-page__card multi-agent-page__output-card" aria-labelledby="output-heading">
                        <div className="multi-agent-page__section-heading">
                            <span className="multi-agent-page__step" aria-hidden="true">02</span>
                            <div>
                                <h2 id="output-heading">Your generated output</h2>
                                <p>A starting point for your next adventure.</p>
                            </div>
                        </div>
                        <div className="multi-agent-page__output" role="region" aria-labelledby="output-heading" aria-live="polite" aria-busy={activeAction === "generate"} tabIndex={0}>
                            {workflow ? (
                                <>
                                    <p>Workflow ID: {workflow.workflow_id}</p>
                                    {hasAgentFailures && <p role="alert">One or more agents did not complete successfully. Review the results before recording a decision.</p>}
                                    <AgentOutput title="Planner" result={workflow.planner_result} />
                                    <AgentOutput title="Worker output" result={workflow.worker_result} />
                                    <AgentOutput title="AI reviewer" result={workflow.reviewer_result} />
                                </>
                            ) : (
                                <div className="multi-agent-page__empty">
                                    <span className="multi-agent-page__spark" aria-hidden="true">✧</span>
                                    <h3>Room for your next great idea</h3>
                                    <p>{activeAction === "generate" ? "The agents are processing your request. This may take up to two minutes." : "Enter a request and generate output. The agent responses will appear here."}</p>
                                </div>
                            )}
                        </div>
                        <p className="multi-agent-page__hint">Review all agent responses, including any model errors or fallback messages, before making your decision.</p>
                    </section>
                </div>

                <section className="multi-agent-page__card multi-agent-page__workflow" aria-labelledby="workflow-heading">
                    <div className="multi-agent-page__section-heading">
                        <span className="multi-agent-page__step" aria-hidden="true">03</span>
                        <div>
                            <h2 id="workflow-heading">Workflow status</h2>
                            <p>Check the current stage of your request and human review.</p>
                        </div>
                    </div>
                    <button type="button" disabled={busy || !workflow} onClick={() => {
                        if (workflow) void runRequest("status", `/workflows/${encodeURIComponent(workflow.workflow_id)}`);
                    }}>{activeAction === "status" ? "Checking status…" : "Get workflow status"}</button>
                    <div role="status">
                        {showWorkflowStatus && (
                            <div className="multi-agent-page__workflow-status">
                                <strong>{workflowStatus}</strong>
                                <ol className="multi-agent-page__stages">
                                    <li>Request: {workflow ? "Received" : activeAction === "generate" ? "Processing" : "Not completed"}</li>
                                    <li>Planner: {workflow?.planner_result.status || "Waiting for response"}</li>
                                    <li>Worker: {workflow?.worker_result.status || "Waiting for response"}</li>
                                    <li>Reviewer: {workflow?.reviewer_result.status || "Waiting for response"}</li>
                                    <li>Human review: {workflow?.human_decision.status || "Waiting for output"}</li>
                                </ol>
                            </div>
                        )}
                    </div>
                    <p className="multi-agent-page__hint">Status retrieves this workflow’s saved results and human decision. Individual agent progress becomes available when generation returns.</p>
                </section>

                <section className="multi-agent-page__card multi-agent-page__review" aria-labelledby="review-heading">
                    <div className="multi-agent-page__section-heading">
                        <span className="multi-agent-page__step" aria-hidden="true">04</span>
                        <div>
                            <h2 id="review-heading">Human review</h2>
                            <p>Accept, partially accept, or reject the output and explain your decision.</p>
                        </div>
                    </div>
                    <form onSubmit={submitFeedback}>
                        <fieldset disabled={!workflow || busy}>
                            <legend>Your response</legend>
                            <div className="multi-agent-page__choices">
                                {reviewOptions.map((option) => (
                                    <label className="multi-agent-page__choice" key={option.value}>
                                        <input
                                            type="radio"
                                            name="review-decision"
                                            value={option.value}
                                            checked={decision === option.value}
                                            onChange={() => { setDecision(option.value); setConfirmation(""); }}
                                            required
                                        />
                                        <span><strong>{option.label}</strong><small>{option.description}</small></span>
                                    </label>
                                ))}
                            </div>
                            <label htmlFor="review-feedback">Reason for your decision (required)</label>
                            <textarea
                                id="review-feedback"
                                rows={3}
                                value={feedback}
                                onChange={(event) => { setFeedback(event.target.value); setReasonError(""); setConfirmation(""); }}
                                placeholder="Explain why the output meets your needs, which parts you accept and would change, or why you reject it."
                                required
                                aria-describedby="review-reason-hint review-reason-error"
                                aria-invalid={Boolean(reasonError)}
                            />
                            <p id="review-reason-hint" className="multi-agent-page__hint">Use at least 20 characters. Refer to specific parts of the output to support your decision.</p>
                            <p id="review-reason-error" className="multi-agent-page__error" role="alert">{reasonError}</p>
                            <label htmlFor="review-evidence">Evidence used <span className="multi-agent-page__optional">(optional)</span></label>
                            <textarea
                                id="review-evidence"
                                rows={3}
                                value={evidence}
                                onChange={(event) => { setEvidence(event.target.value); setConfirmation(""); }}
                                placeholder="Reference relevant IDs, the plan, generated output, or review findings that support your reason."
                            />
                        </fieldset>
                        <div className="multi-agent-page__review-footer">
                            <p className="multi-agent-page__hint">{workflow ? "Your review will be saved against this workflow and itinerary. It does not automatically change the itinerary." : "Generate output to unlock feedback."}</p>
                            <button type="submit" disabled={!workflow || busy || !decision}>{activeAction === "review" ? "Saving decision…" : "Record human decision"} <span aria-hidden="true">→</span></button>
                        </div>
                        <p className="multi-agent-page__confirmation" role="status">{confirmation}</p>
                        {savedReview && (
                            <div className="multi-agent-page__record">
                                <h3>Recorded review</h3>
                                <dl>
                                    <dt>Decision</dt>
                                    <dd>{savedReview.decision}</dd>
                                    <dt>Reason</dt>
                                    <dd>{savedReview.reason}</dd>
                                    {savedReview.evidence && <><dt>Evidence used</dt><dd>{savedReview.evidence}</dd></>}
                                </dl>
                            </div>
                        )}
                    </form>
                </section>
            </div>
        </main>
    );
}

export default MultiAgentServiceIntegration;
