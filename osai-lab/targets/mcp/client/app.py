# MCP Client - intentionally vulnerable
# Vulns: blindly trusts MCP server output, no sanitization of tool results,
#        injects tool results directly into LLM context, no output filtering

from fastapi import FastAPI
import httpx
import os
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Vulnerable MCP Client")

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8005")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


@app.post("/chat")
async def chat(payload: dict):
    """
    Chat endpoint that uses MCP tools to answer questions.
    VULN: Tool results injected directly into LLM prompt without sanitization.
    VULN: LLM can be tricked into calling dangerous tools via prompt injection.
    """
    user_message = payload.get("message", "")
    logger.info(f"Chat request: {user_message}")

    # Step 1: Get available tools from MCP server
    async with httpx.AsyncClient(timeout=30.0) as client:
        tools_resp = await client.get(f"{MCP_SERVER_URL}/tools")
        tools = tools_resp.json().get("tools", [])

    tool_descriptions = "\n".join(
        [f"- {t['name']}: {t['description']}" for t in tools]
    )

    # Step 2: Ask LLM which tool to use
    plan_prompt = f"""You have access to these tools via an MCP server:
{tool_descriptions}

User request: {user_message}

Decide which tool to use and respond with JSON:
{{"tool": "tool_name", "params": {{...}}}}

If no tool is needed, respond with: {{"tool": "none", "response": "your answer"}}
Respond ONLY with JSON."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        llm_resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3", "prompt": plan_prompt, "stream": False},
        )
        llm_text = llm_resp.json().get("response", "{}")

    try:
        decision = json.loads(llm_text)
    except json.JSONDecodeError:
        return {"response": llm_text, "error": "LLM returned non-JSON"}

    if decision.get("tool") == "none":
        return {"response": decision.get("response", llm_text)}

    # Step 3: Call the MCP tool
    tool_name = decision.get("tool")
    tool_params = decision.get("params", {})
    logger.info(f"Calling MCP tool: {tool_name} with params: {tool_params}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        tool_resp = await client.post(
            f"{MCP_SERVER_URL}/tool/{tool_name}", json=tool_params
        )
        tool_result = tool_resp.json()

    # VULN: Tool result injected directly into prompt without sanitization
    # VULN: Tool result could contain prompt injection payloads
    final_prompt = f"""User asked: {user_message}

Tool '{tool_name}' returned this result:
{json.dumps(tool_result)}

Provide a helpful response based on the tool result."""

    async with httpx.AsyncClient(timeout=120.0) as client:
        final_resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": "llama3", "prompt": final_prompt, "stream": False},
        )
        final_text = final_resp.json().get("response", "")

    return {
        "response": final_text,
        "tool_used": tool_name,
        "tool_result": tool_result,  # VULN: exposes raw tool output to user
    }


@app.post("/tool/direct")
async def direct_tool_call(payload: dict):
    """
    VULN: Direct tool invocation endpoint - bypasses LLM entirely.
    Allows attacker to call any MCP tool directly.
    """
    tool_name = payload.get("tool")
    tool_params = payload.get("params", {})
    logger.info(f"Direct tool call: {tool_name}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{MCP_SERVER_URL}/tool/{tool_name}", json=tool_params
        )
        return resp.json()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mcp-client"}
