# CLAUDE.md - OSAI+ Lab

## Project Overview
Local AI Red Teaming lab for OffSec AI-300 (OSAI+) certification prep. Intentionally vulnerable AI services in Docker, attacked from a Kali VM.

## Architecture
- **Mac Host**: Docker Desktop running all containers, VMware Fusion running Kali
- **Kali VM**: 192.168.19.128 on VMware vmnet (bridge101 NAT)
- **Mac on vmnet**: 192.168.19.1 — Kali's gateway to all Docker services
- **Docker network**: ai-lab-net (external), 192.168.100.0/24
- **All services reachable from Kali at**: 192.168.19.1:<port>

## Key Files
- `osai-lab/docker-compose.yml` — all 16 services
- `osai-lab/targets/` — vulnerable app source code (Python/FastAPI)
- `osai-lab/attacker-tools/` — attack scripts for Kali
- `osai-lab/network-setup.sh` — creates Docker network (run on Mac)
- `osai-lab/docs/` — networking docs, attack guide

## Conventions
- All vulnerabilities marked with `# VULN:` comments — preserve them
- Every service has a `/health` endpoint
- Services log all requests to stdout
- Base image: `python:3.11-slim` for all custom containers
- Docker network `ai-lab-net` is external (created by network-setup.sh)
- ChromaDB pinned to 0.5.23 (client and server must match)

## Port Assignments
8000=ChromaDB, 8001=RAG, 8002=Orchestrator, 8003=FileWorker, 8004=ShellWorker,
8005=MCP-Server, 8006=MCP-Client, 8007=Registry, 8008=Pipeline, 8009=ModelAPI,
8010=Embedding, 5432=Postgres, 6379=Redis, 9000/9001=MinIO, 9443=Portainer,
11434=Ollama, 16686=Jaeger

## Do NOT
- Add security controls to vulnerable services
- Change the Docker subnet (192.168.100.0/24)
- Change published port numbers without updating attacker tools
- Use `chromadb:latest` image — must stay pinned at 0.5.23
