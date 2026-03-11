# Module 3: MCP Server

## Overview

A Model Context Protocol (MCP) server that exposes tools for file reading, HTTP fetching, database queries, and command execution. A companion MCP client uses an LLM to decide which tools to call based on user input, then injects tool results into the LLM context. This simulates an AI application that extends LLM capabilities with external tools — the pattern used by ChatGPT plugins, Claude MCP, and similar architectures.

## Services

| Service | Port | Role |
|---|---|---|
| **mcp-server** | :8005 | MCP tool server — exposes file_read, http_fetch, db_query, exec_cmd |
| **mcp-client** | :8006 | LLM-powered client — selects and calls MCP tools, returns results |
| **postgres** | :5432 | PostgreSQL database — users, secrets, and audit tables |
| **ollama** | :11434 | LLM backend (shared) |

## How It Works

### MCP Server
Exposes four tools via a simple REST API. Each tool is called via `POST /tool/{tool_name}` with a JSON payload. No authentication. No input validation.

### MCP Client
1. User sends a message via `/chat`
2. Client fetches available tools from the MCP server
3. LLM decides which tool to use based on the user's message
4. Client calls the selected tool on the MCP server
5. Tool result is injected directly into a follow-up LLM prompt
6. Final LLM response (and raw tool output) returned to user

The client also has a `/tool/direct` endpoint that lets you call any MCP tool without going through the LLM.

## Database Contents

PostgreSQL is pre-loaded with juicy data for SQL injection exercises:

**users table**: usernames, plaintext passwords, roles, API keys
```
admin / SuperSecret123! / admin / sk-admin-key-abc123
alice / Password1!      / user  / sk-alice-key-xyz789
bob   / qwerty          / user  / sk-bob-key-def456
svc-account / service-pass-2026 / service / sk-svc-key-svc999
```

**secrets table**: API keys and credentials
```
OPENAI_API_KEY, AWS_SECRET_KEY, DB_PASSWORD, STRIPE_SECRET, JWT_SIGNING_KEY
```

## Attack Surface

### SQL Injection via db_query
The `db_query` tool executes raw SQL with no parameterization. Full read/write access to the database.

- Endpoint: `POST /tool/db_query`
- Payload: `{"query": "SELECT * FROM secrets"}`
- Can read, modify, or delete any data. Can use `COPY` for file operations.

### SSRF via http_fetch
The `http_fetch` tool fetches any URL with no allowlist. Follows redirects. Can reach internal services, cloud metadata endpoints, and the internal Docker network.

- Endpoint: `POST /tool/http_fetch`
- Payload: `{"url": "http://192.168.100.62:6379/"}`
- Can scan internal network, access Redis, hit cloud metadata

### RCE via exec_cmd
The `exec_cmd` tool runs shell commands with no validation. Uses `shell=True`.

- Endpoint: `POST /tool/exec_cmd`
- Payload: `{"command": "id && cat /etc/shadow"}`

### Path Traversal via file_read
The `file_read` tool reads any file on the container's filesystem.

- Endpoint: `POST /tool/file_read`
- Payload: `{"path": "/etc/passwd"}`

### Tool Injection via MCP Client
The MCP client injects tool results directly into the LLM prompt. If a tool returns data containing prompt injection payloads, the LLM can be manipulated. An attacker can also craft messages that trick the LLM into calling dangerous tools.

- Endpoint: `POST /chat` on mcp-client (:8006)
- Also: `POST /tool/direct` bypasses LLM entirely

## Key Endpoints

### MCP Server (:8005)
| Method | Path | Description |
|---|---|---|
| GET | `/tools` | List all available tools |
| POST | `/tool/file_read` | Read a file (path traversal) |
| POST | `/tool/http_fetch` | Fetch a URL (SSRF) |
| POST | `/tool/db_query` | Execute SQL (injection) |
| POST | `/tool/exec_cmd` | Run a command (RCE) |
| GET | `/health` | Health check |

### MCP Client (:8006)
| Method | Path | Description |
|---|---|---|
| POST | `/chat` | LLM-powered chat with tool use |
| POST | `/tool/direct` | Call any MCP tool directly (bypass LLM) |
| GET | `/health` | Health check |

### PostgreSQL (:5432)
Direct access with `psql -h 192.168.19.1 -U admin -d appdb` (password: `admin123`)

## OSAI+ Topics
- MCP tool injection
- Server-Side Request Forgery (SSRF) via AI tools
- SQL injection through LLM tool interfaces
- Remote code execution via tool APIs
- Indirect prompt injection via tool results
- Authentication bypass on MCP servers
