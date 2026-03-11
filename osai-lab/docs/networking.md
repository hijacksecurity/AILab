# OSAI+ Lab Networking

## Topology

```
┌──────────────────────────┐
│  Kali VM (VMware Fusion) │
│  192.168.19.128          │
│  eth0 on vmnet (NAT)     │
└──────────┬───────────────┘
           │
    VMware bridge101
    (192.168.19.0/24)
           │
┌──────────┴───────────────┐
│  Mac Host                │
│  bridge101: 192.168.19.1 │ ◄── Kali hits this IP
│  en0: 172.21.1.37 (LAN)  │
│  Docker Desktop VM       │
└──────────┬───────────────┘
           │
    Docker published ports
    (0.0.0.0:<port>)
           │
┌──────────┴───────────────┐
│  Docker bridge: ai-lab-net│
│  192.168.100.0/24        │
│                          │
│  .20  rag-app            │
│  .21  chromadb           │
│  .22  ollama             │
│  .30  agent-orchestrator │
│  .31  agent-worker-file  │
│  .32  agent-worker-shell │
│  .40  mcp-server         │
│  .41  mcp-client         │
│  .42  mcp-postgres       │
│  .50  model-registry     │
│  .51  pipeline-runner    │
│  .52  minio              │
│  .60  model-api          │
│  .61  embedding-service  │
│  .62  redis              │
│  .70  portainer          │
│  .71  jaeger             │
└──────────────────────────┘
```

## How Traffic Flows

### Kali -> Containers (attacks)

Kali sends to `192.168.19.1:<port>`. Docker Desktop on the Mac publishes container ports on all host interfaces (`0.0.0.0`), which includes `bridge101` (the VMware NAT interface). Docker's port mapping forwards traffic into the container.

No custom routing or IP forwarding needed.

### Containers -> Kali (reverse shells)

Containers have internet access via Docker's default NAT. The Mac host routes between Docker's internal network and VMware's network. A container can reach `192.168.19.128` (Kali) through the Mac host.

Use `192.168.19.128` as `LHOST` for reverse shell payloads.

### Containers -> Containers (internal)

Containers communicate directly on the `ai-lab-net` Docker bridge (`192.168.100.0/24`) using their static IPs. This traffic never leaves Docker.

### Containers -> Internet

Containers have outbound internet via Docker Desktop's NAT. This is needed for:
- Ollama pulling models
- ChromaDB downloading embedding models
- More realistic SSRF attacks

## Port Map (from Kali)

All services at `192.168.19.1`:

| Port | Service | Protocol |
|---|---|---|
| 8001 | RAG App | HTTP |
| 8000 | ChromaDB | HTTP |
| 11434 | Ollama | HTTP |
| 8002 | Agent Orchestrator | HTTP |
| 8003 | Agent File Worker | HTTP |
| 8004 | Agent Shell Worker | HTTP |
| 8005 | MCP Server | HTTP |
| 8006 | MCP Client | HTTP |
| 5432 | PostgreSQL | TCP |
| 8007 | Model Registry | HTTP |
| 8008 | Pipeline Runner | HTTP |
| 9000 | MinIO S3 API | HTTP |
| 9001 | MinIO Console | HTTP |
| 8009 | Model API | HTTP |
| 8010 | Embedding Service | HTTP |
| 6379 | Redis | TCP |
| 9443 | Portainer | HTTPS |
| 16686 | Jaeger UI | HTTP |
| 4317 | Jaeger OTLP gRPC | gRPC |

## Why This Setup

Docker Desktop for Mac runs containers inside a Linux VM, so Docker bridge networks (`192.168.100.0/24`) aren't directly routable from the Mac host. Published ports (`-p`) are the only path in. This is different from Docker on Linux where the bridge is a real host interface.

We chose this over alternatives:
- **macvlan on vmnet**: Fragile on Mac, breaks host-to-container communication
- **Docker `internal: true`**: Blocks internet — breaks Ollama model pulls and SSRF realism
- **Host-only only**: No internet for setup or realistic attack scenarios
- **Linux VM for Docker**: More "correct" but adds unnecessary complexity
