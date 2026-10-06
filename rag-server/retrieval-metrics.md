# Shared RAG Retrieval Metrics

## Evaluation Summary

The Shared RAG retrieval pipeline was evaluated using five representative
queries covering the five student feature areas.

Evaluation date: 2026-10-01

| Feature | P@5 | R@5 |
|---|---:|---:|
| Traveller Preferences | 1.00 | 0.50 |
| Booking & Itinerary | 1.00 | 0.33 |
| Budget | 1.00 | 0.50 |
| Travel Plan | 0.40 | 1.00 |
| Pre-trip | 1.00 | 0.67 |
| **Average** | **0.88** | **0.60** |

## Evaluation Method

Precision@5 measures the proportion of the top five retrieved chunks that
belong to the expected relevant source types for the query.

Recall@5 is evaluated at the project source-type level. It measures how many
of the expected relevant source types are represented in the top five
retrieval results.

This source-level Recall@5 is used because the project does not contain a
fully manually labelled relevance dataset covering every chunk in the shared
corpus.

## Results

The evaluation achieved an average Precision@5 of 0.88 and an average
source-level Recall@5 of 0.60.

Traveller Preferences, Booking & Itinerary, Budget, and Pre-trip queries
returned highly relevant chunks in the top five results.

The Travel Plan query retrieved the correct Japan travel plan as the highest
ranked result. Other Japan-related shared project data, including packing
lists and pre-trip tasks, were also retrieved because the Shared RAG corpus
contains context from multiple feature services.

The evaluation demonstrates that semantic retrieval can identify relevant
project context across the five integrated feature areas.

## Retrieval Configuration

- Vector store: ChromaDB
- Embedding model: nomic-embed-text through local Ollama
- Retrieval method: semantic vector retrieval
- Top-K: 5
- Corpus size during evaluation: 196 chunks
- RAG execution: local and non-containerised