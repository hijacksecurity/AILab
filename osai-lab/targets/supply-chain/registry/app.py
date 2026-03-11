# Model Registry - intentionally vulnerable
# Vulns: no model signature verification, arbitrary uploads, no auth,
#        path traversal on model names, metadata tampering

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import os
import json
import logging
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Model Registry")

MODELS_DIR = "/app/models"


@app.post("/models/upload")
async def upload_model(
    model_name: str,
    file: UploadFile = File(...),
    metadata: str = "{}",
):
    """
    VULN: No signature verification on uploaded models.
    VULN: No auth - anyone can upload/replace models.
    VULN: Path traversal via model_name parameter.
    """
    logger.info(f"Model upload: {model_name}")

    # VULN: model_name used directly in path - path traversal
    model_path = os.path.join(MODELS_DIR, f"{model_name}.pkl")
    content = await file.read()

    with open(model_path, "wb") as f:
        f.write(content)

    # Store metadata alongside model - no validation
    meta = json.loads(metadata)
    meta["filename"] = model_name
    meta["size"] = len(content)
    meta["sha256"] = hashlib.sha256(content).hexdigest()
    # VULN: no signature field required

    meta_path = os.path.join(MODELS_DIR, f"{model_name}.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    return {"status": "uploaded", "model": model_name, "size": len(content)}


@app.get("/models/{model_name}")
async def download_model(model_name: str):
    """VULN: No auth, serves models without verification"""
    model_path = os.path.join(MODELS_DIR, f"{model_name}.pkl")
    if not os.path.exists(model_path):
        return {"error": "Model not found"}
    return FileResponse(model_path, media_type="application/octet-stream")


@app.get("/models/{model_name}/metadata")
async def model_metadata(model_name: str):
    meta_path = os.path.join(MODELS_DIR, f"{model_name}.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            return json.load(f)
    return {"error": "Metadata not found"}


@app.get("/models")
async def list_models():
    """VULN: Lists all models with full metadata"""
    models = []
    for fname in os.listdir(MODELS_DIR):
        if fname.endswith(".pkl"):
            name = fname.replace(".pkl", "")
            meta_path = os.path.join(MODELS_DIR, f"{name}.json")
            meta = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    meta = json.load(f)
            models.append({"name": name, "metadata": meta})
    return {"models": models}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "model-registry"}
