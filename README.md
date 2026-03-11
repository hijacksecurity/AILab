# OSAI+ Lab

Local AI Red Teaming lab mapped to the OffSec AI-300 (OSAI+) syllabus. Intentionally vulnerable AI services running in Docker on a Mac host, attacked from a Kali Linux VM via VMware Fusion.

## Architecture

```
Kali VM (192.168.19.128)  ──►  Mac Host (192.168.19.1)  ──►  Docker Containers
      VMware vmnet                  Published ports             192.168.100.0/24
```

Kali reaches all services at `192.168.19.1:<port>`. Containers talk to each other on the Docker bridge at `192.168.100.x`. Reverse shells route back from containers to Kali via Docker NAT.

## Quick Start

```bash
# On Mac host
cd osai-lab
./network-setup.sh
docker compose up -d --build

# Wait for Ollama to pull models (~5-10 min first time)
docker logs -f ollama

# On Kali VM
cd osai-lab/attacker-tools
python3 -m venv venv && source venv/bin/activate
pip install httpx
python3 lab_check.py
```

Import `osai-lab/attacker-tools/bookmarks.html` into Firefox on Kali for organized access to all service UIs.

## Lab Modules

| # | Module | Services | Ports | Primary Attacks |
|---|---|---|---|---|
| 1 | **RAG Pipeline** | rag-app, chromadb, ollama | :8001, :8000, :11434 | Prompt injection, doc poisoning, path traversal |
| 2 | **Multi-Agent System** | orchestrator, worker-file, worker-shell | :8002, :8003, :8004 | Agent hijacking, A2A abuse, tool manipulation |
| 3 | **MCP Server** | mcp-server, mcp-client, postgres | :8005, :8006, :5432 | SSRF, SQLi, RCE, tool injection |
| 4 | **AI Supply Chain** | model-registry, pipeline-runner, minio | :8007, :8008, :9000 | Pickle RCE, model poisoning, S3 misconfig |
| 5 | **AI Infrastructure** | model-api, embedding-service, redis | :8009, :8010, :6379 | Model extraction, timing oracle, cache poisoning |

Plus **Portainer** (:9443) and **Jaeger** (:16686) for monitoring.

## Documentation

| Doc | Description |
|---|---|
| [Lab Overview](osai-lab/docs/lab-overview.md) | Full service map, module summary, shared infrastructure |
| [Module 1 — RAG Pipeline](osai-lab/docs/module1-rag.md) | Prompt injection, document poisoning, data exfiltration |
| [Module 2 — Multi-Agent System](osai-lab/docs/module2-agents.md) | Agent hijacking, A2A protocol, worker exploitation |
| [Module 3 — MCP Server](osai-lab/docs/module3-mcp.md) | Tool injection, SSRF, SQLi, RCE |
| [Module 4 — AI Supply Chain](osai-lab/docs/module4-supply-chain.md) | Pickle RCE, model poisoning, registry abuse |
| [Module 5 — AI Infrastructure](osai-lab/docs/module5-infra.md) | Model extraction, timing attacks, cache poisoning |
| [Networking](osai-lab/docs/networking.md) | Network topology, traffic flows, port map |
| [Attack Guide](osai-lab/docs/attack-guide.md) | Per-module attack commands and examples |
| [Lab Credentials](osai-lab/docs/lab-credentials.md) | Management creds, backing service access, lab reset |

## Attacker Tools

Located in `osai-lab/attacker-tools/`, run from Kali:

| Tool | Module | Description |
|---|---|---|
| `lab_check.py` | All | Functional health check for entire lab |
| `bookmarks.html` | All | Firefox bookmarks for all service UIs |
| `rag_injector.py` | 1 | Prompt injection via document poisoning |
| `agent_hijacker.py` | 2 | A2A manipulation, goal hijacking, direct worker access |
| `mcp_exploiter.py` | 3 | SSRF, SQLi, RCE, tool injection |
| `supply_chain_attack.py` | 4 | Pickle RCE, model poisoning, registry redirect |
| `model_extractor.py` | 5 | Model extraction, timing oracle, cache poisoning |

## Notes

- All `VULN:` comments in source code mark intentional vulnerabilities
- Every service has a `/health` endpoint and Swagger UI at `/docs`
- All services log to stdout — use `docker compose logs -f <service>` to watch attacks
- Ollama needs at least 8GB memory in Docker Desktop settings
