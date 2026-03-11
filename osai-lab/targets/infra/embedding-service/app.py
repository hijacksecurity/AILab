# Embedding Service - intentionally vulnerable
# Vulns: no rate limiting, timing oracle, cache poisoning, embedding inversion,
#        no auth, exposes cached embeddings

from fastapi import FastAPI
import httpx
import redis
import os
import json
import time
import hashlib
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Embedding Service")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_EMBEDDINGS = os.getenv("CACHE_EMBEDDINGS", "true").lower() == "true"
TIMING_PROTECTION = os.getenv("TIMING_PROTECTION", "false").lower() == "true"

redis_client = None


@app.on_event("startup")
async def startup():
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None


@app.post("/embed")
async def embed(payload: dict):
    """
    Generate embeddings for text.
    VULN: Timing oracle - cached vs uncached response times differ.
    VULN: No rate limiting - enables embedding space exploration.
    """
    text = payload.get("text", "")
    model = payload.get("model", "llama3")

    logger.info(f"Embed request: {text[:50]}...")

    start_time = time.time()
    cache_hit = False

    # Check cache
    cache_key = f"emb:{hashlib.sha256(f'{model}:{text}'.encode()).hexdigest()}"

    if CACHE_EMBEDDINGS and redis_client:
        cached = redis_client.get(cache_key)
        if cached:
            cache_hit = True
            embedding = json.loads(cached)
            elapsed = time.time() - start_time

            # VULN: Timing oracle - cache hits are much faster
            if not TIMING_PROTECTION:
                return {
                    "embedding": embedding,
                    "model": model,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "cached": True,
                }

    # Generate embedding via Ollama
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": model, "prompt": text},
        )

    result = resp.json()
    embedding = result.get("embedding", [])

    # Cache the embedding
    if CACHE_EMBEDDINGS and redis_client:
        redis_client.set(cache_key, json.dumps(embedding), ex=3600)

    elapsed = time.time() - start_time

    return {
        "embedding": embedding,
        "model": model,
        "dimensions": len(embedding),
        "elapsed_ms": round(elapsed * 1000, 2),  # VULN: timing info
        "cached": cache_hit,
    }


@app.post("/embed/batch")
async def embed_batch(payload: dict):
    """
    Batch embedding endpoint.
    VULN: No rate limiting, enables efficient embedding space mapping.
    """
    texts = payload.get("texts", [])
    model = payload.get("model", "llama3")

    results = []
    for text in texts[:100]:
        resp = await embed({"text": text, "model": model})
        results.append(resp)

    return {"results": results, "count": len(results)}


@app.post("/similarity")
async def similarity(payload: dict):
    """Compare similarity between two texts - useful for adversarial research"""
    text_a = payload.get("text_a", "")
    text_b = payload.get("text_b", "")
    model = payload.get("model", "llama3")

    emb_a = await embed({"text": text_a, "model": model})
    emb_b = await embed({"text": text_b, "model": model})

    vec_a = emb_a.get("embedding", [])
    vec_b = emb_b.get("embedding", [])

    if vec_a and vec_b:
        import numpy as np

        a = np.array(vec_a)
        b = np.array(vec_b)
        cosine_sim = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    else:
        cosine_sim = 0.0

    return {
        "text_a": text_a[:50],
        "text_b": text_b[:50],
        "cosine_similarity": cosine_sim,
    }


@app.get("/cache/dump")
async def cache_dump():
    """VULN: Dumps all cached embeddings - enables embedding inversion attacks"""
    if not redis_client:
        return {"error": "Redis not available"}

    keys = redis_client.keys("emb:*")
    entries = {}
    for key in keys[:500]:
        entries[key] = json.loads(redis_client.get(key))

    return {"cached_embeddings": len(entries), "entries": entries}


@app.post("/cache/set")
async def cache_set(payload: dict):
    """
    VULN: Direct cache write - enables cache poisoning.
    Attacker can inject arbitrary embeddings for any text.
    """
    text = payload.get("text", "")
    model = payload.get("model", "llama3")
    embedding = payload.get("embedding", [])

    cache_key = f"emb:{hashlib.sha256(f'{model}:{text}'.encode()).hexdigest()}"

    if redis_client:
        redis_client.set(cache_key, json.dumps(embedding), ex=3600)
        return {"status": "cached", "key": cache_key}
    return {"error": "Redis not available"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "embedding-service"}
