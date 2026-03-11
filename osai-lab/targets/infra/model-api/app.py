# Model Inference API - intentionally vulnerable
# Vulns: model info leakage, no rate limiting, input logging (data exposure),
#        no auth, model extraction via unlimited queries, adversarial input acceptance

from fastapi import FastAPI
import httpx
import redis
import os
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Model API")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

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


@app.post("/inference")
async def inference(payload: dict):
    """
    Run inference on the model.
    VULN: No rate limiting - enables model extraction via many queries.
    VULN: All inputs logged - data exposure.
    VULN: No input validation - accepts adversarial inputs.
    """
    prompt = payload.get("prompt", "")
    model = payload.get("model", "llama3")
    temperature = payload.get("temperature", 0.7)

    logger.info(f"Inference request: model={model} prompt={prompt[:100]}")

    # VULN: Log all inputs to Redis (data exposure if Redis is accessed)
    if redis_client:
        redis_client.lpush(
            "inference_log",
            json.dumps({"prompt": prompt, "model": model, "timestamp": time.time()}),
        )

    start_time = time.time()

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )

    elapsed = time.time() - start_time
    result = resp.json()

    return {
        "response": result.get("response", ""),
        "model": model,
        "elapsed_ms": round(elapsed * 1000, 2),  # VULN: timing info leaked
        "tokens": result.get("eval_count", 0),
        "prompt_tokens": result.get("prompt_eval_count", 0),
    }


@app.get("/models")
async def list_models():
    """VULN: Exposes all available models and their details"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
    return resp.json()


@app.get("/model/{model_name}/info")
async def model_info(model_name: str):
    """VULN: Leaks model architecture, parameters, and configuration"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{OLLAMA_URL}/api/show", json={"name": model_name}
        )
    return resp.json()


@app.get("/stats")
async def stats():
    """VULN: Exposes usage statistics and query logs"""
    if not redis_client:
        return {"error": "Redis not available"}

    recent_logs = redis_client.lrange("inference_log", 0, 99)
    parsed = [json.loads(log) for log in recent_logs]

    return {
        "total_queries": redis_client.llen("inference_log"),
        "recent_queries": parsed,
    }


@app.post("/batch")
async def batch_inference(payload: dict):
    """
    Batch inference endpoint.
    VULN: No rate limiting, enables efficient model extraction.
    """
    prompts = payload.get("prompts", [])
    model = payload.get("model", "llama3")

    results = []
    for prompt in prompts[:50]:  # soft limit, but no rate limiting
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
        results.append(resp.json().get("response", ""))

    return {"model": model, "results": results, "count": len(results)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "model-api"}
