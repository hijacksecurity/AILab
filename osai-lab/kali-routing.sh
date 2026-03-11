#!/bin/bash
# Run inside Kali VM to verify connectivity to Docker lab targets.
# All services are reachable via the Mac host at 192.168.19.1:<port>.
# No custom routing needed — Mac is already Kali's default gateway.

set -e

HOST="192.168.19.1"

echo "[*] OSAI+ Lab Connectivity Check"
echo "[*] Target host: $HOST"
echo ""

declare -A TARGETS=(
  ["RAG App"]="$HOST:8001"
  ["ChromaDB"]="$HOST:8000"
  ["Ollama"]="$HOST:11434"
  ["Agent Orchestrator"]="$HOST:8002"
  ["Agent File Worker"]="$HOST:8003"
  ["Agent Shell Worker"]="$HOST:8004"
  ["MCP Server"]="$HOST:8005"
  ["MCP Client"]="$HOST:8006"
  ["Model Registry"]="$HOST:8007"
  ["Pipeline Runner"]="$HOST:8008"
  ["Model API"]="$HOST:8009"
  ["Embedding Service"]="$HOST:8010"
)

pass=0
fail=0

for name in "${!TARGETS[@]}"; do
  addr="${TARGETS[$name]}"
  if curl -s --connect-timeout 2 "http://$addr/health" > /dev/null 2>&1; then
    echo "  [+] $name  =>  http://$addr  ✓"
    ((pass++))
  else
    echo "  [-] $name  =>  http://$addr  ✗"
    ((fail++))
  fi
done

echo ""
echo "[*] Results: $pass reachable, $fail unreachable"
