# Lab Credentials (Non-Victim Infrastructure)

These are credentials for managing the lab itself — not part of the attack exercises.

## Lab Management

| Service | URL | Username | Password | Purpose |
|---|---|---|---|---|
| Portainer | https://192.168.19.1:9443 | admin | labpassword | Docker container management UI |
| Jaeger | http://192.168.19.1:16686 | (none) | (none) | Distributed tracing — view request flows |

## Backing Services

These are the databases and caches that the vulnerable apps depend on. Direct access is useful for resetting state, inspecting data, or watching attacks in real time.

| Service | Access | Credentials | Notes |
|---|---|---|---|
| PostgreSQL | `psql -h 192.168.19.1 -U admin -d appdb` | admin / admin123 | Backs MCP module. Contains users & secrets tables. |
| Redis | `redis-cli -h 192.168.19.1 -p 6379` | (no auth) | Backs Model API & Embedding modules. Stores query logs & cached embeddings. |
| ChromaDB | http://192.168.19.1:8000 | (no auth) | Backs RAG module. Stores document embeddings. |
| MinIO | http://192.168.19.1:9001 (console) | minioadmin / minioadmin | Backs Supply Chain module. S3-compatible model storage. |
| Ollama | http://192.168.19.1:11434 | (no auth) | Shared LLM backend. Serves llama3 and mistral. |

## Resetting the Lab

```bash
# On Mac host, from osai-lab/
# Full reset — wipe all data and restart
docker compose down -v
docker compose up -d

# Reset just one module's data
docker compose restart rag-app chromadb          # Module 1
docker compose restart agent-orchestrator agent-worker-file agent-worker-shell  # Module 2
docker compose restart mcp-server mcp-client mcp-postgres   # Module 3
docker compose restart model-registry pipeline-runner minio  # Module 4
docker compose restart model-api embedding-service redis     # Module 5
```
