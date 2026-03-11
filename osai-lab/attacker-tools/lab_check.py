#!/usr/bin/env python3
"""
OSAI+ Lab Health Check - Run from Kali VM
Performs app-specific functional checks against each lab target.
"""

import httpx
import sys
import json
import time

HOST = "192.168.19.1"
TIMEOUT = 10.0

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def header(text):
    width = 62
    print(f"\n{CYAN}{BOLD}{'=' * width}{RESET}")
    print(f"{CYAN}{BOLD}  {text}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * width}{RESET}")


def section(name, port, desc):
    print(f"\n{BOLD}  [{name}]{RESET} {DIM}:{port}{RESET} - {desc}")


def ok(msg):
    print(f"    {GREEN}[+]{RESET} {msg}")


def fail(msg):
    print(f"    {RED}[-]{RESET} {msg}")


def warn(msg):
    print(f"    {YELLOW}[!]{RESET} {msg}")


def info(msg):
    print(f"    {DIM}    {msg}{RESET}")


def check_health(client, port):
    try:
        r = client.get(f"http://{HOST}:{port}/health")
        return r.status_code == 200
    except Exception:
        return False


def check_rag(client, results):
    section("RAG App", 8001, "Vulnerable RAG pipeline")
    if not check_health(client, 8001):
        fail("Service unreachable")
        results.append(("RAG App", False))
        return

    ok("Service is up")

    # Check if documents are ingested
    try:
        r = client.get(f"http://{HOST}:8001/documents")
        docs = r.json()
        # Response is {"documents": {"ids": [...], ...}}
        inner = docs.get("documents", docs)
        doc_ids = inner.get("ids", []) if isinstance(inner, dict) else []
        count = len(doc_ids) if isinstance(doc_ids, list) else 0
        if count > 0:
            ok(f"Document store: {count} docs ingested")
            for did in doc_ids[:5]:
                info(f"doc: {did}")
        else:
            warn("No documents ingested yet")
    except Exception as e:
        warn(f"Could not list documents: {e}")

    # Check ChromaDB
    try:
        r = client.get(f"http://{HOST}:8000/api/v1/heartbeat")
        if r.status_code == 200:
            ok("ChromaDB backend reachable (no auth)")
        else:
            warn(f"ChromaDB returned {r.status_code}")
    except Exception:
        fail("ChromaDB unreachable")

    # Check Ollama
    try:
        r = client.get(f"http://{HOST}:11434/api/tags")
        models = [m["name"] for m in r.json().get("models", [])]
        if models:
            ok(f"Ollama models available: {', '.join(models)}")
        else:
            warn("Ollama running but no models pulled yet")
    except Exception:
        fail("Ollama unreachable")

    results.append(("RAG App", True))


def check_agents(client, results):
    section("Agent Orchestrator", 8002, "Multi-agent system with tool workers")
    if not check_health(client, 8002):
        fail("Orchestrator unreachable")
        results.append(("Agent System", False))
        return

    ok("Orchestrator is up")

    # Enumerate agents - should expose topology
    try:
        r = client.get(f"http://{HOST}:8002/agents")
        data = r.json()
        agents = data.get("agents", [])
        for a in agents:
            ok(f"Agent: {a['name']} @ {a['url']} ({a['role']})")
        sys_prompt = data.get("system_prompt", "")
        if sys_prompt:
            warn(f"System prompt leaked: \"{sys_prompt[:80]}...\"")
    except Exception as e:
        warn(f"Could not enumerate agents: {e}")

    # Check file worker directly (no auth)
    try:
        r = client.post(
            f"http://{HOST}:8003/execute",
            json={"action": "list", "path": "/"},
        )
        entries = r.json().get("entries", [])
        if entries:
            ok(f"File worker: no auth, root listing returned {len(entries)} entries")
        else:
            warn("File worker responded but returned empty listing")
    except Exception:
        fail("File worker unreachable at :8003")

    # Check shell worker directly (no auth)
    try:
        r = client.post(
            f"http://{HOST}:8004/execute",
            json={"action": "exec", "command": "id"},
        )
        stdout = r.json().get("stdout", "").strip()
        if stdout:
            ok(f"Shell worker: no auth, command exec works -> {stdout}")
        else:
            warn("Shell worker responded but no output")
    except Exception:
        fail("Shell worker unreachable at :8004")

    results.append(("Agent System", True))


def check_mcp(client, results):
    section("MCP Server", 8005, "Vulnerable MCP with SQLi, SSRF, RCE tools")
    if not check_health(client, 8005):
        fail("MCP Server unreachable")
        results.append(("MCP Server", False))
        return

    ok("MCP Server is up")

    # Enumerate tools
    try:
        r = client.get(f"http://{HOST}:8005/tools")
        tools = r.json().get("tools", [])
        for t in tools:
            ok(f"Tool: {t['name']} - {t['description']}")
    except Exception as e:
        warn(f"Could not list tools: {e}")

    # Test SQLi - query users table
    try:
        r = client.post(
            f"http://{HOST}:8005/tool/db_query",
            json={"query": "SELECT username, role FROM users LIMIT 3"},
        )
        data = r.json()
        rows = data.get("results", [])
        if rows:
            ok(f"SQLi via db_query: returned {len(rows)} rows from users table")
            for row in rows:
                info(f"user: {row}")
        else:
            warn("db_query returned no results")
    except Exception as e:
        warn(f"db_query failed: {e}")

    # Test file_read
    try:
        r = client.post(
            f"http://{HOST}:8005/tool/file_read",
            json={"path": "/etc/hostname"},
        )
        content = r.json().get("content", "").strip()
        if content:
            ok(f"Path traversal via file_read: /etc/hostname -> {content}")
    except Exception:
        warn("file_read tool failed")

    # Check MCP Client
    if check_health(client, 8006):
        ok("MCP Client is up (trusts MCP output blindly)")
    else:
        warn("MCP Client unreachable at :8006")

    # Check Postgres directly
    try:
        r = client.post(
            f"http://{HOST}:8005/tool/db_query",
            json={"query": "SELECT count(*) FROM secrets"},
        )
        count = r.json().get("results", [[0]])[0][0]
        ok(f"Postgres has {count} rows in secrets table")
    except Exception:
        warn("Could not query secrets table")

    results.append(("MCP Server", True))


def check_supply_chain(client, results):
    section("Model Registry", 8007, "Supply chain - model poisoning & pickle RCE")
    if not check_health(client, 8007):
        fail("Model Registry unreachable")
        results.append(("Supply Chain", False))
        return

    ok("Model Registry is up")

    # List models
    try:
        r = client.get(f"http://{HOST}:8007/models")
        models = r.json().get("models", [])
        if models:
            ok(f"Registry: {len(models)} models available (no signature verification)")
            for m in models:
                info(f"model: {m['name']}")
        else:
            warn("Registry is empty - upload models to test supply chain attacks")
    except Exception as e:
        warn(f"Could not list models: {e}")

    # Check pipeline runner
    if check_health(client, 8008):
        ok("Pipeline Runner is up (pickle.load on untrusted data)")
    else:
        warn("Pipeline Runner unreachable at :8008")

    # Check MinIO
    try:
        r = client.get(f"http://{HOST}:9000/minio/health/live")
        if r.status_code == 200:
            ok("MinIO S3 is up (default creds: minioadmin/minioadmin)")
        else:
            warn(f"MinIO returned {r.status_code}")
    except Exception:
        warn("MinIO unreachable at :9000")

    results.append(("Supply Chain", True))


def check_infra(client, results):
    section("Model API", 8009, "Model extraction, adversarial inputs")
    if not check_health(client, 8009):
        fail("Model API unreachable")
        results.append(("AI Infra", False))
        return

    ok("Model API is up")

    # Check model info leakage
    try:
        r = client.get(f"http://{HOST}:8009/models")
        models = r.json().get("models", [])
        if models:
            ok(f"Model info leaked: {len(models)} models exposed")
            for m in models:
                name = m.get("name", "unknown")
                size = m.get("size", 0)
                info(f"model: {name} ({size // (1024*1024) if isinstance(size, int) and size > 0 else '?'}MB)")
        else:
            warn("No models listed (Ollama may still be pulling)")
    except Exception as e:
        warn(f"Could not list models: {e}")

    # Check stats endpoint (query log exposure)
    try:
        r = client.get(f"http://{HOST}:8009/stats")
        data = r.json()
        total = data.get("total_queries", 0)
        ok(f"Stats endpoint exposed: {total} queries logged")
    except Exception:
        warn("Stats endpoint unavailable")

    # Check embedding service
    section("Embedding Service", 8010, "Timing oracle, cache poisoning")
    if not check_health(client, 8010):
        fail("Embedding Service unreachable")
        return

    ok("Embedding Service is up")

    # Test timing oracle - first request (cache miss) vs second (cache hit)
    try:
        text = "osai lab timing test"
        t1_start = time.time()
        r1 = client.post(f"http://{HOST}:8010/embed", json={"text": text})
        t1 = (time.time() - t1_start) * 1000
        cached1 = r1.json().get("cached", False)

        t2_start = time.time()
        r2 = client.post(f"http://{HOST}:8010/embed", json={"text": text})
        t2 = (time.time() - t2_start) * 1000
        cached2 = r2.json().get("cached", False)

        dims = r1.json().get("dimensions", "?")
        ok(f"Embeddings working: {dims} dimensions")
        ok(f"Timing oracle: miss={t1:.0f}ms (cached={cached1}), hit={t2:.0f}ms (cached={cached2})")
    except Exception as e:
        warn(f"Embedding test failed: {e}")

    # Check cache dump
    try:
        r = client.get(f"http://{HOST}:8010/cache/dump")
        count = r.json().get("cached_embeddings", 0)
        ok(f"Cache dump endpoint exposed: {count} cached embeddings")
    except Exception:
        warn("Cache dump endpoint unavailable")

    # Check Redis
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((HOST, 6379))
        s.send(b"PING\r\n")
        resp = s.recv(64).decode().strip()
        s.close()
        if "PONG" in resp:
            ok("Redis reachable with no auth -> PONG")
        else:
            warn(f"Redis responded: {resp}")
    except Exception:
        warn("Redis unreachable at :6379")

    results.append(("AI Infra", True))


def check_monitoring(client, results):
    section("Portainer", 9443, "Container management UI")
    try:
        # Portainer uses self-signed HTTPS — need a separate client with verify=False
        with httpx.Client(timeout=TIMEOUT, verify=False) as https_client:
            r = https_client.get(f"https://{HOST}:9443/")
            if r.status_code in (200, 301, 302):
                ok("Portainer UI reachable (HTTPS, admin/labpassword)")
            else:
                warn(f"Portainer returned {r.status_code}")
    except Exception as e:
        warn(f"Portainer unreachable: {e}")

    section("Jaeger", 16686, "Distributed tracing UI")
    try:
        r = client.get(f"http://{HOST}:16686/")
        if r.status_code == 200:
            ok("Jaeger UI reachable")
    except Exception:
        warn("Jaeger unreachable")


def check_reverse_shell_path(client, results):
    section("Reverse Shell Path", "", "Container -> Kali connectivity")
    # Get Kali's IP on the VMware NAT network
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((HOST, 80))
        kali_ip = s.getsockname()[0]
        s.close()
    except Exception:
        kali_ip = "unknown"

    if kali_ip != "unknown":
        ok(f"Kali IP on lab network: {kali_ip}")
        info("Containers route back to Kali via Docker NAT -> Mac host -> vmnet")
        info(f"Use {kali_ip} as LHOST for reverse shells")
    else:
        warn("Could not determine Kali's IP")


def main():
    header("OSAI+ Lab Health Check")
    print(f"  {DIM}Target: {HOST}  |  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}{RESET}")

    results = []

    with httpx.Client(timeout=TIMEOUT) as client:
        check_rag(client, results)
        check_agents(client, results)
        check_mcp(client, results)
        check_supply_chain(client, results)
        check_infra(client, results)
        check_monitoring(client, results)
        check_reverse_shell_path(client, results)

    # Summary
    header("Summary")
    passed = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, status in results:
        icon = f"{GREEN}PASS{RESET}" if status else f"{RED}FAIL{RESET}"
        print(f"    {icon}  {name}")

    print(f"\n  {BOLD}{passed}/{total} modules operational{RESET}")

    if passed < total:
        print(f"  {YELLOW}Some modules are down - check docker compose logs <service>{RESET}")
        sys.exit(1)
    else:
        print(f"  {GREEN}Lab is fully operational. Happy hacking!{RESET}\n")


if __name__ == "__main__":
    main()
