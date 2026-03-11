#!/bin/bash
# OSAI+ Lab Network Setup (Mac Host)
# Creates the Docker bridge network for lab containers.
# Kali reaches containers via Mac's bridge101 IP (192.168.19.1) + published ports.
# No IP forwarding or custom routing needed.

set -e

DOCKER_SUBNET="192.168.100.0/24"
DOCKER_NETWORK="ai-lab-net"

echo "[*] Creating Docker lab network..."
docker network create \
  --driver bridge \
  --subnet $DOCKER_SUBNET \
  $DOCKER_NETWORK 2>/dev/null && echo "    Network created." || echo "    Network already exists."

echo ""
echo "[*] Network setup complete."
echo ""
echo "    Kali reaches all services at 192.168.19.1:<port>"
echo ""
echo "    Port Map:"
echo "      RAG App:           192.168.19.1:8001"
echo "      ChromaDB:          192.168.19.1:8000"
echo "      Ollama:            192.168.19.1:11434"
echo "      Agent Orchestrator: 192.168.19.1:8002"
echo "      Agent File Worker:  192.168.19.1:8003"
echo "      Agent Shell Worker: 192.168.19.1:8004"
echo "      MCP Server:        192.168.19.1:8005"
echo "      MCP Client:        192.168.19.1:8006"
echo "      Postgres:          192.168.19.1:5432"
echo "      Model Registry:    192.168.19.1:8007"
echo "      Pipeline Runner:   192.168.19.1:8008"
echo "      MinIO:             192.168.19.1:9000 (console: 9001)"
echo "      Model API:         192.168.19.1:8009"
echo "      Embedding Service: 192.168.19.1:8010"
echo "      Redis:             192.168.19.1:6379"
echo "      Portainer:         192.168.19.1:9443"
echo "      Jaeger UI:         192.168.19.1:16686"
