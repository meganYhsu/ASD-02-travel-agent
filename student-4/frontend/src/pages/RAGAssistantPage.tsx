import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import "../styles/RAGAssistantPage.css";

type RagCitation = {
    chunk_id: string;
    source_id: string;
    authority_tier: string;
};

type RagResult = {
    answer: string;
    citations: RagCitation[];
    confidenceCategory: string;
    retrievalSummary: {
        k?: number;
        retrieved_count?: number;
        top_chunk?: string | null;
    } | null;
};

type RagPageState = {
    itineraryId?: number;
    destination?: string;
    startDate?: string;
    endDate?: string;
};

function RAGAssistantPage() {
    const location = useLocation();
    const navigate = useNavigate();
    const context = (location.state || {}) as RagPageState;
    const [question, setQuestion] = useState("What activities are included in this travel plan?");
    const [result, setResult] = useState<RagResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const contextPrefix = useMemo(() => {
        const parts = [];

        if (context.itineraryId) {
            parts.push(`itinerary ID ${context.itineraryId}`);
        }

        if (context.destination) {
            parts.push(`destination ${context.destination}`);
        }

        if (context.startDate && context.endDate) {
            parts.push(`dates ${context.startDate} to ${context.endDate}`);
        }

        return parts.length > 0
            ? `For saved ${parts.join(", ")}: `
            : "";
    }, [context]);

    async function askSharedRag(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        const trimmedQuestion = question.trim();
        if (!trimmedQuestion) {
            setError("Enter a question about saved itineraries.");
            return;
        }

        try {
            setLoading(true);
            setError("");
            setResult(null);

            const response = await fetch("http://localhost:5004/api/rag/ask", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    question: `${contextPrefix}${trimmedQuestion}`
                })
            });

            const payload = await response.json();

            if (!response.ok || !payload?.success) {
                throw new Error(payload?.error || "Shared RAG request failed");
            }

            setResult(payload.data);
        } catch (err) {
            const message = err instanceof Error ? err.message : "Shared RAG request failed";
            setError(message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="rag-assistant-page">
            <div className="rag-assistant-page__shell">
                <header className="rag-assistant-page__hero">
                    <p className="rag-assistant-page__eyebrow">Shared RAG</p>
                    <h1 className="rag-assistant-page__title">Travel plan search</h1>
                    <p className="rag-assistant-page__intro">
                        Ask questions about saved itineraries and retrieve grounded project context with source chunks.
                    </p>
                </header>

                <section className="rag-assistant-page__panel">
                    <div className="rag-assistant-page__section-head">
                        <div>
                            <p className="rag-assistant-page__eyebrow">Question</p>
                            <h2 className="rag-assistant-page__section-title">Ask about saved travel plans</h2>
                        </div>
                        <div className="rag-assistant-page__meta">
                            {context.itineraryId ? `Itinerary ${context.itineraryId}` : "All saved plans"}
                        </div>
                    </div>

                    {contextPrefix && (
                        <p className="rag-assistant-page__context">
                            {contextPrefix.replace(/: $/, "")}
                        </p>
                    )}

                    <form className="rag-assistant-page__form" onSubmit={askSharedRag}>
                        <input
                            className="rag-assistant-page__input"
                            type="text"
                            value={question}
                            onChange={(event) => setQuestion(event.target.value)}
                            placeholder="Ask about itinerary ID, destination, location, date, activity, or budget"
                        />
                        <button
                            className="rag-assistant-page__button"
                            type="submit"
                            disabled={loading}
                        >
                            {loading ? "Searching..." : "Ask RAG"}
                        </button>
                    </form>

                    {error && (
                        <div className="rag-assistant-page__state rag-assistant-page__state--error">
                            {error}
                        </div>
                    )}

                    {result && (
                        <article className="rag-assistant-page__result">
                            <div className="rag-assistant-page__result-head">
                                <p className="rag-assistant-page__eyebrow">Retrieved context</p>
                                <span>{result.confidenceCategory}</span>
                            </div>
                            <p className="rag-assistant-page__answer">{result.answer}</p>
                            <div className="rag-assistant-page__summary">
                                <span>Top chunk: {result.retrievalSummary?.top_chunk || "None"}</span>
                                <span>Retrieved: {result.retrievalSummary?.retrieved_count || 0}</span>
                            </div>
                            {result.citations.length > 0 && (
                                <div className="rag-assistant-page__citations">
                                    {result.citations.map((citation) => (
                                        <span key={citation.chunk_id}>
                                            {citation.chunk_id}
                                        </span>
                                    ))}
                                </div>
                            )}
                        </article>
                    )}
                </section>

                <section className="rag-assistant-page__actions">
                    <button
                        className="rag-assistant-page__button"
                        type="button"
                        onClick={() => navigate(-1)}
                    >
                        Back
                    </button>
                    <button
                        className="rag-assistant-page__button rag-assistant-page__button--secondary"
                        type="button"
                        onClick={() => navigate("/")}
                    >
                        Back to planner
                    </button>
                </section>
            </div>
        </div>
    );
}

export default RAGAssistantPage;
