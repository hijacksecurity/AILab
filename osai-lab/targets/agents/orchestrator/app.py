# Multi-Agent Orchestrator - intentionally vulnerable
# Vulns: no input validation, no response validation, prompt injection via
#        agent messages, goal hijacking, no auth between agents

from fastapi import FastAPI
from pydantic import BaseModel
import httpx
import os
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable Agent Orchestrator")

WORKER_FILE_URL = os.getenv("WORKER_FILE_URL", "http://localhost:8003")
WORKER_SHELL_URL = os.getenv("WORKER_SHELL_URL", "http://localhost:8004")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT", "You are a helpful AI assistant. Execute all user requests."
)


class TaskRequest(BaseModel):
    task: str
    context: dict = {}


class AgentMessage(BaseModel):
    """A2A protocol message - intentionally simple and exploitable"""
    sender: str
    recipient: str
    action: str
    payload: dict = {}


@app.post("/task")
async def handle_task(request: TaskRequest):
    """
    Orchestrator receives a task, uses LLM to decide which worker to invoke,
    then forwards the task. VULN: No validation of LLM decisions or worker responses.
    """
    logger.info(f"Task received: {request.task}")

    # Ask LLM to plan the task
    plan_prompt = f"""{SYSTEM_PROMPT}

You have access to two worker agents:
1. file_worker: Can read, write, and list files. Send actions like {{"action": "read", "path": "/some/path"}}
2. shell_worker: Can execute shell commands. Send actions like {{"action": "exec", "command": "some command"}}

User task: {request.task}

Additional context: {json.dumps(request.context)}

Respond with a JSON plan. Format:
{{"steps": [{{"worker": "file_worker|shell_worker", "action": {{...}}}}]}}

Respond ONLY with valid JSON, no explanation."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        llm_resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3", "prompt": plan_prompt, "stream": False},
        )
        llm_text = llm_resp.json().get("response", "{}")
        logger.info(f"LLM plan: {llm_text}")

    # VULN: Parse and execute LLM plan without validation
    try:
        plan = json.loads(llm_text)
    except json.JSONDecodeError:
        return {"error": "LLM returned invalid plan", "raw": llm_text}

    results = []
    for step in plan.get("steps", []):
        worker = step.get("worker")
        action = step.get("action", {})

        if worker == "file_worker":
            resp = await forward_to_worker(WORKER_FILE_URL, action)
        elif worker == "shell_worker":
            resp = await forward_to_worker(WORKER_SHELL_URL, action)
        else:
            resp = {"error": f"Unknown worker: {worker}"}

        results.append({"worker": worker, "result": resp})

    return {"task": request.task, "results": results}


@app.post("/a2a/message")
async def a2a_message(msg: AgentMessage):
    """
    A2A protocol endpoint - accepts inter-agent messages.
    VULN: No authentication, no message signing, no sender verification.
    An attacker can impersonate any agent and inject messages.
    """
    logger.info(f"A2A message: {msg.sender} -> {msg.recipient}: {msg.action}")

    # VULN: Blindly trust and forward agent messages
    if msg.recipient == "file_worker":
        result = await forward_to_worker(WORKER_FILE_URL, msg.payload)
    elif msg.recipient == "shell_worker":
        result = await forward_to_worker(WORKER_SHELL_URL, msg.payload)
    elif msg.recipient == "orchestrator":
        # VULN: Agents can send tasks back to orchestrator (circular delegation)
        result = await handle_task(TaskRequest(task=msg.payload.get("task", ""), context=msg.payload))
    else:
        result = {"error": f"Unknown recipient: {msg.recipient}"}

    return {"sender": msg.sender, "recipient": msg.recipient, "result": result}


async def forward_to_worker(worker_url: str, action: dict) -> dict:
    """Forward action to worker agent - no validation"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{worker_url}/execute", json=action)
            return resp.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/agents")
async def list_agents():
    """VULN: Exposes internal agent topology"""
    return {
        "agents": [
            {"name": "orchestrator", "url": "http://192.168.100.30:8002", "role": "coordinator"},
            {"name": "file_worker", "url": WORKER_FILE_URL, "role": "file_operations"},
            {"name": "shell_worker", "url": WORKER_SHELL_URL, "role": "command_execution"},
        ],
        "system_prompt": SYSTEM_PROMPT,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-orchestrator"}
