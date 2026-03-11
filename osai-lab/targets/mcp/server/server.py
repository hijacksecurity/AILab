# Vulnerable MCP Server
# Vulns: no auth, SSRF via http_fetch, SQLi via db_query, path traversal via
#        file_read, RCE via exec_cmd, tool list manipulation

from fastapi import FastAPI
import httpx
import psycopg2
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable MCP Server")

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "dbname": os.getenv("DB_NAME"),
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.get("/tools")
async def list_tools():
    """VULN: Tool list is static and can be manipulated by injecting tool descriptions"""
    return {
        "tools": [
            {
                "name": "file_read",
                "description": "Read contents of a file",
                "parameters": {"path": "string"},
            },
            {
                "name": "http_fetch",
                "description": "Fetch content from a URL",
                "parameters": {"url": "string"},
            },
            {
                "name": "db_query",
                "description": "Execute a database query",
                "parameters": {"query": "string"},
            },
            {
                "name": "exec_cmd",
                "description": "Execute a system command",
                "parameters": {"command": "string"},
            },
        ]
    }


@app.post("/tool/http_fetch")
async def tool_http_fetch(payload: dict):
    # VULN: SSRF - no URL validation or allowlist
    url = payload.get("url")
    logger.info(f"http_fetch: {url}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url, follow_redirects=True)
    return {"content": resp.text, "status": resp.status_code}


@app.post("/tool/db_query")
async def tool_db_query(payload: dict):
    # VULN: SQLi - raw query execution
    query = payload.get("query")
    logger.info(f"db_query: {query}")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query)  # VULN: direct execution - no parameterization

    # Handle both SELECT and non-SELECT queries
    try:
        columns = [desc[0] for desc in cur.description] if cur.description else []
        results = cur.fetchall()
        conn.commit()
        conn.close()
        return {"columns": columns, "results": results}
    except Exception:
        conn.commit()
        conn.close()
        return {"status": "executed", "rowcount": cur.rowcount}


@app.post("/tool/file_read")
async def tool_file_read(payload: dict):
    # VULN: Path traversal - no restriction
    path = payload.get("path")
    logger.info(f"file_read: {path}")
    with open(path, "r") as f:
        return {"content": f.read()}


@app.post("/tool/exec_cmd")
async def tool_exec_cmd(payload: dict):
    # VULN: RCE - no command validation
    cmd = payload.get("command")
    logger.info(f"exec_cmd: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-server"}
