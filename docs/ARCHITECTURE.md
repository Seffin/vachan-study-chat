# Architecture Overview

Vachan Study is a layered scripture study application that combines a modern frontend experience with a retrieval-first backend. The product is designed to feel conversational, multilingual, and grounded in scripture, while also remaining resilient when external services are unavailable.

## System Layers

- Frontend: A Next.js interface for book selection, chat, suggestion chips, scripture reading, and voice-first interaction.
- Backend: A FastAPI service that handles language detection, hybrid retrieval, reranking, translation fallback, and SSE streaming.
- Data layer: MongoDB Atlas for history and repository-backed data, plus local scripture assets and datasets for fast fallback and offline support.
- AI layer: Optional language model providers for high-quality generation, with graceful fallback to local retrieval when needed.

## Request Flow

1. The user sends a message from the chat workspace.
2. The frontend posts the request to the backend chat endpoint along with the selected book and recent history.
3. The backend detects the language, runs hybrid retrieval, and reranks candidates.
4. If a strong match is found, the backend returns the dataset-backed answer and reference. Otherwise it tries translation fallback and then AI generation.
5. The backend streams status updates and the final result back to the frontend over Server-Sent Events.
6. The frontend updates the chat, highlights the referenced verse, and refreshes follow-up suggestions.
7. If the backend is unavailable, the frontend switches to its local simulator so the experience still remains usable.

This structure keeps the product easy to extend while preserving a strong user experience for study, reference, and exploration.
