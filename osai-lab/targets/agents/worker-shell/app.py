# Agent Worker - Shell Execution - intentionally vulnerable
# Vulns: arbitrary command execution, no auth, no command allowlist, env leakage

from fastapi import FastAPI
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Shell Worker Agent")

COMMAND_ALLOWLIST = os.getenv("COMMAND_ALLOWLIST", "")  # VULN: empty = allow all


@app.post("/execute")
async def execute(payload: dict):
    action = payload.get("action", "")
    logger.info(f"Shell worker action: {action} | payload: {payload}")

    if action == "exec":
        return await exec_command(payload.get("command", ""))
    elif action == "env":
        return await get_env()
    elif action == "ps":
        return await list_processes()
    else:
        return {"error": f"Unknown action: {action}"}


async def exec_command(command: str):
    # VULN: Arbitrary command execution with shell=True
    # VULN: No allowlist enforcement, no sanitization
    logger.info(f"Executing command: {command}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "action": "exec",
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"action": "exec", "command": command, "error": "Command timed out"}
    except Exception as e:
        return {"action": "exec", "command": command, "error": str(e)}


async def get_env():
    # VULN: Dumps all environment variables
    return {"action": "env", "environment": dict(os.environ)}


async def list_processes():
    # VULN: Exposes running processes
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    return {"action": "ps", "processes": result.stdout}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-worker-shell"}
