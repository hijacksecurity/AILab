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
pip install httpx
python3 lab_check.py    # from attacker-tools/
```

## Services

| Module | Service | Kali Access | Primary Vulns |
|---|---|---|---|
| **RAG Pipeline** | rag-app | :8001 | Prompt injection, path traversal, data exfil |
| | chromadb | :8000 | No auth |
| | ollama | :11434 | Open API |
| **Multi-Agent** | orchestrator | :8002 | Prompt injection, goal hijacking, topology leak |
| | worker-file | :8003 | No auth, path traversal, host filesystem access |
| | worker-shell | :8004 | No auth, arbitrary command execution |
| **MCP Server** | mcp-server | :8005 | SSRF, SQLi, RCE, path traversal |
| | mcp-client | :8006 | Blind trust of MCP output, tool injection |
| | postgres | :5432 | Weak creds (admin/admin123) |
| **Supply Chain** | model-registry | :8007 | No signature verification, arbitrary upload |
| | pipeline-runner | :8008 | pickle RCE, registry redirect |
| | minio | :9000 | Default creds (minioadmin/minioadmin) |
| **AI Infra** | model-api | :8009 | Model extraction, info leak, no rate limit |
| | embedding-service | :8010 | Timing oracle, cache poisoning, cache dump |
| | redis | :6379 | No auth |
| **Monitoring** | portainer | :9443 | Container management UI |
| | jaeger | :16686 | Distributed tracing UI |

## Attacker Tools

Located in `osai-lab/attacker-tools/`, designed to run from Kali:

| Tool | Target | Attack |
|---|---|---|
| `lab_check.py` | All | Functional health check for entire lab |
| `rag_injector.py` | RAG | Prompt injection via document poisoning |
| `agent_hijacker.py` | Agents | A2A manipulation, goal hijacking, direct worker access |
| `mcp_exploiter.py` | MCP | SSRF, SQLi, RCE, tool injection |
| `supply_chain_attack.py` | Supply Chain | Pickle RCE, model poisoning, registry redirect |
| `model_extractor.py` | Infra | Model extraction, timing oracle, cache poisoning |

## OSAI+ Module Coverage

| OSAI Module | Lab Target | Attack Path |
|---|---|---|
| Recon for AI Targets | All services | Port scan, API enumeration, model fingerprinting |
| Attacking AI Agents | orchestrator | Prompt injection, goal hijacking |
| Multi-Agent / A2A | worker-* | A2A message tampering, worker impersonation |
| Exploiting RAG | rag-app + chromadb | Doc poisoning, indirect injection, data exfil |
| Attacking Embeddings | embedding-service | Embedding inversion, cache poisoning, timing oracle |
| Attacking MCP | mcp-server | Tool injection, SSRF, SQLi via tools |
| AI Supply Chain | registry + pipeline | Pickle RCE, model poisoning, S3 misconfig |
| AI Infra Exploits | model-api | Model extraction, adversarial inputs |
| Threat Modeling | All | Documentation exercise per target |
| Capstone | Full lab chain | Multi-stage: recon -> RAG -> agent pivot -> supply chain RCE |

## Docs

- [Networking](osai-lab/docs/networking.md) — full network topology, traffic flows, port map
- [Attack Guide](osai-lab/docs/attack-guide.md) — per-module attack commands and examples

## Notes

- All `VULN:` comments in source code mark intentional vulnerabilities
- Every service has a `/health` endpoint
- All services log to stdout — use `docker compose logs <service>` to watch attacks
- Ollama needs at least 8GB memory in Docker Desktop settings
