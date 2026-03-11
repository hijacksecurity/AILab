# Pipeline runner - vulnerable to pickle RCE and model poisoning
# Vulns: pickle.load on untrusted models, no checksum verification,
#        no model allowlist, arbitrary registry URLs accepted, S3 misconfiguration

from fastapi import FastAPI
import httpx
import pickle
import os
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Pipeline Runner")

REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8007")
S3_URL = os.getenv("S3_URL", "http://localhost:9000")


@app.post("/run")
async def run_pipeline(payload: dict):
    """
    Run inference pipeline with a model from registry.
    VULN: pickle.load on untrusted data = RCE
    VULN: caller controls registry URL
    VULN: no checksum verification
    """
    model_name = payload.get("model_name")
    # VULN: Caller can override registry URL to point to attacker-controlled server
    registry_url = payload.get("registry_url", REGISTRY_URL)
    input_data = payload.get("input", [[1, 2, 3]])

    logger.info(f"Pipeline run: model={model_name} registry={registry_url}")

    # Pull model from registry - no signature verification
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{registry_url}/models/{model_name}")

    if resp.status_code != 200:
        return {"error": f"Failed to fetch model: {resp.status_code}"}

    model_path = f"/tmp/{model_name}.pkl"
    with open(model_path, "wb") as f:
        f.write(resp.content)

    actual_hash = hashlib.sha256(resp.content).hexdigest()
    logger.info(f"Model downloaded: {model_name} sha256={actual_hash}")

    # VULN: pickle.load on untrusted data = arbitrary code execution
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    # Run inference
    try:
        result = model.predict(input_data)
        return {
            "model": model_name,
            "input": input_data,
            "result": str(result),
            "sha256": actual_hash,
        }
    except Exception as e:
        return {"model": model_name, "error": str(e)}


@app.post("/run-from-s3")
async def run_from_s3(payload: dict):
    """
    VULN: Load model directly from S3/MinIO - no verification.
    Demonstrates supply chain attack via compromised object storage.
    """
    bucket = payload.get("bucket", "models")
    key = payload.get("key")

    logger.info(f"S3 pipeline run: bucket={bucket} key={key}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{S3_URL}/{bucket}/{key}")

    if resp.status_code != 200:
        return {"error": f"Failed to fetch from S3: {resp.status_code}"}

    model_path = f"/tmp/s3_{key}"
    with open(model_path, "wb") as f:
        f.write(resp.content)

    # VULN: Same pickle.load vulnerability
    with open(model_path, "rb") as f:
        model = pickle.load(f)

    try:
        result = model.predict(payload.get("input", [[1, 2, 3]]))
        return {"source": "s3", "key": key, "result": str(result)}
    except Exception as e:
        return {"source": "s3", "key": key, "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "pipeline-runner"}
