import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

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
    const [question, setQuestion] = useState("");
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
                    // question: `${contextPrefix}${trimmedQuestion}`
                    question: `${trimmedQuestion}`
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
        <div className="saved-itinerary-page">
            <div className="saved-itinerary-page__shell">
                <header className="saved-itinerary-page__hero">
                    <p className="saved-itinerary-page__eyebrow">Question</p>
                    <h1 className="saved-itinerary-page__title">Ask about saved travel plans</h1>
                    {contextPrefix && (
                        <p className="saved-itinerary-page__intro">
                            {contextPrefix.replace(/: $/, "")}
                        </p>
                    )}
                </header>

                <section className="saved-itinerary-page__panel">
                    <form className="saved-itinerary-page__section-head" onSubmit={askSharedRag}>
                        <input
                            className="rag-assistant-page__input"
                            type="text"
                            value={question}
                            onChange={(event) => setQuestion(event.target.value)}
                            placeholder="Ask about itinerary activities, dates, budget, or locations."
                        />
                        <button
                            className="saved-itinerary-page__button"
                            type="submit"
                            disabled={loading}
                        >
                            {loading ? "Searching..." : "Ask RAG"}
                        </button>
                    </form>

                    <p className="rag-assistant-page__note">
                        Note: To generate an accurate response, please be specific with your question. Include the itinerary ID, such as itinerary ID {context.itineraryId || "(itinerary ID)"}, and keywords like activities, dates, budget, or locations.
                    </p>

                    {error && (
                        <div className="saved-itinerary-page__state saved-itinerary-page__state--error">
                            {error}
                        </div>
                    )}

                    {result && (
                        <article className="saved-itinerary-page__day">
                            <div className="saved-itinerary-page__day-head">
                                <div>
                                    <p className="saved-itinerary-page__eyebrow">Retrieved context</p>
                                </div>
                                <span>{result.confidenceCategory}</span>
                            </div>
                            <p>{result.answer}</p>
                            <div className="saved-itinerary-page__day-meta">
                                <span>Top chunk: {result.retrievalSummary?.top_chunk || "None"}</span>
                                <span>Retrieved: {result.retrievalSummary?.retrieved_count || 0}</span>
                            </div>
                            {result.citations.length > 0 && (
                                <div className="saved-itinerary-page__day-meta">
                                    {result.citations.map((citation) => (
                                        <span key={citation.chunk_id}>{citation.chunk_id}</span>
                                    ))}
                                </div>
                            )}
                        </article>
                    )}
                </section>

                <section className="saved-itinerary-page__actions">
                    <button
                        className="saved-itinerary-page__button"
                        type="button"
                        onClick={() => navigate(-1)}
                    >
                        Back
                    </button>
                    <button
                        className="saved-itinerary-page__button"
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
