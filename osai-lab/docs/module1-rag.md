# Module 1: RAG Pipeline

## Overview

A Retrieval-Augmented Generation (RAG) application that ingests documents into a vector store and uses them as context when answering questions via an LLM. This simulates a corporate knowledge base chatbot — the kind of thing enterprises deploy for internal docs, support tickets, and policy lookup.

## Services

| Service | Port | Role |
|---|---|---|
| **rag-app** | :8001 | FastAPI app — handles document ingestion and LLM-powered queries |
| **chromadb** | :8000 | ChromaDB vector database — stores document embeddings, no auth |
| **ollama** | :11434 | LLM backend — serves llama3 and mistral (shared with other modules) |

## How It Works

1. Documents are uploaded via `/ingest` — stored on disk and embedded into ChromaDB
2. User sends a query via `/query`
3. App retrieves the 5 most relevant document chunks from ChromaDB
4. Retrieved chunks are injected into an LLM prompt as context
5. LLM generates an answer and returns it — no output filtering

## Attack Surface

### Prompt Injection via Document Poisoning
The core vulnerability. Documents ingested into the vector store are retrieved and injected directly into the LLM prompt with zero sanitization. An attacker uploads a document containing prompt injection payloads. When a user's query triggers retrieval of that document, the injected instructions override the system behavior.

**Why it works:** The LLM can't distinguish between legitimate document content and injected instructions. The poisoned document becomes part of the trusted context.

- Endpoint: `POST /ingest`
- No file type validation
- No content sanitization before embedding
- Retrieved documents injected verbatim into LLM prompt

### Path Traversal on Upload
The uploaded filename is used directly in the file path (`/app/uploads/{filename}`). A filename like `../../etc/cron.d/backdoor` writes outside the intended directory.

- Endpoint: `POST /ingest`
- Filename from multipart form used without sanitization

### Data Exfiltration
The `/documents` endpoint returns all stored documents with full content — no access control. ChromaDB is also directly accessible on `:8000` with no authentication.

- Endpoint: `GET /documents` (lists all docs with content)
- ChromaDB API: `http://192.168.19.1:8000/docs` (full API access)

### No Output Sanitization
LLM responses are returned to the user without any filtering. If the LLM is tricked into outputting credentials, internal data, or injection payloads, they pass through unmodified.

## Key Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/ingest` | Upload and ingest a document |
| POST | `/query` | Query the RAG pipeline |
| GET | `/documents` | List all ingested documents (data leak) |
| GET | `/health` | Health check |

## OSAI+ Topics
- Indirect prompt injection
- RAG poisoning
- Data exfiltration via LLM
- Document store enumeration
- Vector database security
