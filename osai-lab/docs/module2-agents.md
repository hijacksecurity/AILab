# Module 2: Multi-Agent System

## Overview

A multi-agent AI system with a central orchestrator that delegates tasks to specialized worker agents. The orchestrator uses an LLM to plan task execution, then forwards actions to a file operations worker and a shell execution worker. This simulates enterprise AI agent deployments where multiple AI components coordinate to complete tasks.

## Services

| Service | Port | Role |
|---|---|---|
| **orchestrator** | :8002 | Central coordinator — receives tasks, uses LLM to plan, dispatches to workers |
| **worker-file** | :8003 | File operations agent — read, write, list, search files |
| **worker-shell** | :8004 | Shell execution agent — runs arbitrary commands as root |
| **ollama** | :11434 | LLM backend (shared) |

## How It Works

1. User submits a task to the orchestrator via `/task`
2. Orchestrator sends the task to the LLM with descriptions of available workers
3. LLM returns a JSON plan specifying which workers to invoke and with what actions
4. Orchestrator executes the plan by forwarding actions to workers
5. Results are collected and returned — no validation of worker responses

The orchestrator also exposes an `/a2a/message` endpoint for direct inter-agent communication using a simple Agent-to-Agent (A2A) protocol.

## Attack Surface

### Agent Topology Leak
The `/agents` endpoint exposes all agent URLs, roles, internal IPs, and the system prompt. This gives an attacker a complete map of the agent infrastructure before any exploitation.

- Endpoint: `GET /agents`
- Leaks: internal Docker IPs, worker URLs, system prompt

### Direct Worker Access (No Auth)
Both workers accept requests directly on their own ports — no authentication, no verification that the request came from the orchestrator. An attacker can bypass the orchestrator entirely and talk to workers directly.

- File worker: `POST http://192.168.19.1:8003/execute`
- Shell worker: `POST http://192.168.19.1:8004/execute`
- Both accept arbitrary actions with no auth

### Prompt Injection via Task
User-controlled task input is injected directly into the LLM planning prompt. An attacker can craft a task that manipulates the LLM into generating a malicious plan — reading sensitive files, executing commands, or exfiltrating data.

**Why it works:** The orchestrator trusts the LLM's plan output completely. If the LLM is tricked into planning malicious actions, they execute without validation.

### A2A Protocol Manipulation
The `/a2a/message` endpoint accepts messages from any sender with no authentication or signing. An attacker can:
- Impersonate any agent
- Send commands directly to workers via the orchestrator
- Create circular delegation loops (agent -> orchestrator -> agent)

### Tool Abuse
- **File worker** has the host filesystem mounted read-only at `/hostfs`. It can read any file on the Docker host.
- **Shell worker** runs as root with `SYS_PTRACE` capability. No command allowlist.
- **Environment leak**: Shell worker's `/execute` with `action: "env"` dumps all environment variables.

## Key Endpoints

### Orchestrator (:8002)
| Method | Path | Description |
|---|---|---|
| POST | `/task` | Submit a task for LLM-planned execution |
| POST | `/a2a/message` | Send an inter-agent message (no auth) |
| GET | `/agents` | List all agents with URLs and system prompt |
| GET | `/health` | Health check |

### File Worker (:8003)
| Method | Path | Description |
|---|---|---|
| POST | `/execute` | Execute file action: read, write, list, search |
| GET | `/health` | Health check |

### Shell Worker (:8004)
| Method | Path | Description |
|---|---|---|
| POST | `/execute` | Execute action: exec (shell cmd), env (dump env), ps (list processes) |
| GET | `/health` | Health check |

## OSAI+ Topics
- AI agent goal hijacking
- Agent-to-Agent (A2A) protocol security
- Multi-agent prompt injection
- Tool abuse and privilege escalation
- Agent authentication and authorization gaps
- Lateral movement via AI agents
