# Module 5: AI Infrastructure

## Overview

An inference API and embedding service that wrap the Ollama LLM backend with caching, logging, and statistics. The model API exposes model architecture details, logs all queries, and has no rate limiting — enabling model extraction attacks. The embedding service has a timing side-channel between cached and uncached requests, exposes a cache dump endpoint, and accepts direct cache writes — enabling cache poisoning. Both use Redis for storage with no authentication.

This simulates production AI infrastructure where inference endpoints, embedding services, and caches are deployed with insufficient access controls.

## Services

| Service | Port | Role |
|---|---|---|
| **model-api** | :8009 | Inference API — wraps Ollama, logs queries, exposes model info |
| **embedding-service** | :8010 | Embedding API — generates embeddings, caches in Redis |
| **redis** | :6379 | Shared cache — stores embeddings and query logs, no auth |
| **ollama** | :11434 | LLM backend (shared) |

## How It Works

### Model API
Receives inference requests, forwards them to Ollama, logs everything to Redis, and returns the response with timing information and token counts. Also exposes model metadata, architecture details, and query statistics.

### Embedding Service
Generates text embeddings via Ollama and caches them in Redis. Subsequent requests for the same text return the cached embedding instantly — creating a measurable timing difference. Also provides batch embedding, similarity comparison, cache dump, and direct cache write endpoints.

### Redis
Unprotected shared datastore. Stores:
- All inference query logs (prompts, models, timestamps)
- Cached embeddings (keyed by SHA256 of model+text)

## Attack Surface

### Model Extraction via Repeated Queries
The model API has no rate limiting. An attacker can send thousands of input/output pairs to build a dataset for training a surrogate model that replicates the target's behavior. Token counts and timing data in responses help optimize the extraction.

- Endpoint: `POST /inference` (single) and `POST /batch` (up to 50 at once)
- Response includes: token count, prompt token count, elapsed time

### Model Information Leakage
The API exposes full model details — architecture, parameter count, quantization, family — information that aids targeted adversarial attacks.

- Endpoint: `GET /models` — lists all models with sizes
- Endpoint: `GET /model/{name}/info` — full architecture details

### Query Log Exposure
All inference queries are logged to Redis and exposed via the stats endpoint. An attacker can read other users' prompts, see what the model is being used for, and extract sensitive data that was sent to the model.

- Endpoint: `GET /stats` — returns the 100 most recent queries with full prompts
- Redis: `LRANGE inference_log 0 -1` — all queries ever logged

### Timing Side-Channel on Embeddings
Cached embedding requests return in ~5ms. Cache misses take ~500-1500ms (waiting for Ollama). This timing difference reveals whether a specific text has been previously embedded — leaking information about what data the system has processed.

- Endpoint: `POST /embed`
- Response includes `elapsed_ms` and `cached` boolean
- Compare response times to determine cache membership

### Cache Poisoning
The embedding service has a `/cache/set` endpoint that accepts arbitrary embeddings for any text. An attacker can:
- Replace legitimate embeddings with adversarial ones
- Poison similarity searches by making unrelated texts appear similar
- Disrupt downstream systems that depend on embedding quality

- Endpoint: `POST /cache/set` — write any embedding to cache
- Endpoint: `GET /cache/dump` — read all cached embeddings

### Redis (No Auth)
Redis is accessible on `:6379` with no password. Full read/write access to all cached data and query logs.

```bash
redis-cli -h 192.168.19.1 -p 6379
> KEYS *
> LRANGE inference_log 0 -1
> GET emb:<hash>
```

## Key Endpoints

### Model API (:8009)
| Method | Path | Description |
|---|---|---|
| POST | `/inference` | Run inference (logged, timed) |
| POST | `/batch` | Batch inference (up to 50 prompts) |
| GET | `/models` | List models with sizes |
| GET | `/model/{name}/info` | Full model architecture details |
| GET | `/stats` | Query log with recent prompts |
| GET | `/health` | Health check |

### Embedding Service (:8010)
| Method | Path | Description |
|---|---|---|
| POST | `/embed` | Generate embedding (cached, timed) |
| POST | `/embed/batch` | Batch embeddings (up to 100) |
| POST | `/similarity` | Compare two texts via cosine similarity |
| GET | `/cache/dump` | Dump all cached embeddings |
| POST | `/cache/set` | Write arbitrary embedding to cache (poison) |
| GET | `/health` | Health check |

### Redis (:6379)
Direct TCP access with no auth. Use `redis-cli` from Kali.

## OSAI+ Topics
- Model extraction / model stealing
- Adversarial input crafting
- Timing side-channel attacks
- Embedding inversion
- Cache poisoning
- AI infrastructure hardening
- Data leakage via inference logs
