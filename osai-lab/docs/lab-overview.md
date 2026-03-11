# OSAI+ Lab Overview

## What This Is

A local AI Red Teaming lab with 5 attack modules covering the OffSec AI-300 (OSAI+) syllabus. Every service is intentionally vulnerable — no accidental security, no security controls. All 16 containers run on Docker Desktop (Mac host) and are reachable from a Kali Linux VM through VMware Fusion.

## How to Access

All services are at **192.168.19.1** (Mac host's VMware interface) on different ports. Every custom service has a Swagger UI at `/docs` for interactive API exploration.

Import `attacker-tools/bookmarks.html` into Firefox on Kali for organized bookmarks.

## Lab Modules at a Glance

| # | Module | What It Simulates | OSAI+ Topics |
|---|---|---|---|
| 1 | [RAG Pipeline](module1-rag.md) | Corporate knowledge base with LLM chat | Prompt injection, data poisoning, data exfiltration |
| 2 | [Multi-Agent System](module2-agents.md) | AI agent swarm with tool-using workers | Agent hijacking, A2A protocol abuse, tool manipulation |
| 3 | [MCP Server](module3-mcp.md) | Model Context Protocol server with database tools | Tool injection, SSRF, SQL injection, RCE |
| 4 | [AI Supply Chain](module4-supply-chain.md) | ML model registry and inference pipeline | Model poisoning, pickle deserialization RCE, registry abuse |
| 5 | [AI Infrastructure](module5-infra.md) | Model inference API and embedding service | Model extraction, timing side-channels, cache poisoning |

## Service Map

```
MODULE 1 — RAG Pipeline
├── rag-app          :8001   FastAPI app — ingests docs, queries LLM with RAG
├── chromadb         :8000   Vector database — stores document embeddings
└── ollama           :11434  LLM backend — serves llama3 and mistral

MODULE 2 — Multi-Agent System
├── orchestrator     :8002   Central coordinator — plans tasks, dispatches to workers
├── worker-file      :8003   File operations agent — read/write/list/search files
└── worker-shell     :8004   Shell execution agent — runs arbitrary commands

MODULE 3 — MCP Server
├── mcp-server       :8005   MCP tool server — file_read, http_fetch, db_query, exec_cmd
├── mcp-client       :8006   LLM-powered client — calls MCP tools based on user input
└── postgres         :5432   Database — users table, secrets table, audit log

MODULE 4 — AI Supply Chain
├── model-registry   :8007   Model storage — upload/download ML models
├── pipeline-runner  :8008   Inference pipeline — loads and runs models from registry
└── minio            :9000   S3-compatible storage — secondary model storage

MODULE 5 — AI Infrastructure
├── model-api        :8009   Inference API — wraps Ollama with logging and stats
├── embedding-service :8010  Embedding API — generates and caches text embeddings
└── redis            :6379   Cache/datastore — stores embeddings and query logs

MONITORING
├── portainer        :9443   Docker management UI (admin/labpassword)
└── jaeger           :16686  Distributed tracing UI
```

## Shared Infrastructure

**Ollama** (`:11434`) is shared by modules 1, 2, 3, and 5 as the LLM backend. It runs llama3 and mistral.

**Redis** (`:6379`) is shared by modules 5 (model-api and embedding-service) for caching and logging. It has no authentication.

**MinIO** (`:9000`) is part of module 4. It provides S3-compatible object storage as a secondary path for model hosting. In real-world supply chain attacks, compromised S3 buckets are a common vector for swapping legitimate models with poisoned ones. The pipeline runner can pull models from either the registry or MinIO.
