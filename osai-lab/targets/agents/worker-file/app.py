# Agent Worker - File Operations - intentionally vulnerable
# Vulns: path traversal, no auth, exposes host filesystem, no input validation

from fastapi import FastAPI
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable File Worker Agent")

ALLOWED_PATHS = os.getenv("ALLOWED_PATHS", "/")  # VULN: defaults to root


@app.post("/execute")
async def execute(payload: dict):
    action = payload.get("action", "")
    logger.info(f"File worker action: {action} | payload: {payload}")

    if action == "read":
        return await read_file(payload.get("path", ""))
    elif action == "write":
        return await write_file(payload.get("path", ""), payload.get("content", ""))
    elif action == "list":
        return await list_dir(payload.get("path", "/"))
    elif action == "search":
        return await search_files(payload.get("path", "/"), payload.get("pattern", ""))
    else:
        return {"error": f"Unknown action: {action}"}


async def read_file(path: str):
    # VULN: No path validation - can read any file on the filesystem
    try:
        # Map to hostfs if mounted
        effective_path = path
        if os.path.exists(f"/hostfs{path}"):
            effective_path = f"/hostfs{path}"

        with open(effective_path, "r", errors="ignore") as f:
            content = f.read(1024 * 1024)  # 1MB limit for sanity
        return {"action": "read", "path": path, "content": content}
    except Exception as e:
        return {"action": "read", "path": path, "error": str(e)}


async def write_file(path: str, content: str):
    # VULN: Can write anywhere
    try:
        with open(path, "w") as f:
            f.write(content)
        return {"action": "write", "path": path, "status": "written"}
    except Exception as e:
        return {"action": "write", "path": path, "error": str(e)}


async def list_dir(path: str):
    # VULN: Directory listing without restriction
    try:
        effective_path = path
        if os.path.exists(f"/hostfs{path}"):
            effective_path = f"/hostfs{path}"

        entries = os.listdir(effective_path)
        return {"action": "list", "path": path, "entries": entries[:200]}
    except Exception as e:
        return {"action": "list", "path": path, "error": str(e)}


async def search_files(path: str, pattern: str):
    # VULN: Recursive file search
    try:
        effective_path = path
        if os.path.exists(f"/hostfs{path}"):
            effective_path = f"/hostfs{path}"

        matches = []
        for root, dirs, files in os.walk(effective_path):
            for f in files:
                if pattern.lower() in f.lower():
                    matches.append(os.path.join(root, f))
            if len(matches) >= 100:
                break
        return {"action": "search", "path": path, "pattern": pattern, "matches": matches}
    except Exception as e:
        return {"action": "search", "path": path, "error": str(e)}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-worker-file"}
