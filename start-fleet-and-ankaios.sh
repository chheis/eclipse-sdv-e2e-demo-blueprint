#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FLEET_COMPOSE_FILE="${FLEET_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose.yaml}"
FLEET_TRANSPORT_COMPOSE_FILE="${FLEET_TRANSPORT_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose-zenoh.yaml}"
ANKAIOS_MANIFEST="${ANKAIOS_MANIFEST:-${SCRIPT_DIR}/devices/raspberry-pi5/ankaios/vehicle-signals.yaml}"
ANKAIOS_START_WAIT_SECONDS="${ANKAIOS_START_WAIT_SECONDS:-2}"

log() {
  printf "[start] %s\n" "$*"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "[start] Missing required command: %s\n" "$1" >&2
    exit 1
  fi
}

require_file() {
  if [ ! -f "$1" ]; then
    printf "[start] Missing required file: %s\n" "$1" >&2
    exit 1
  fi
}

require_cmd docker
require_cmd ank
require_file "$FLEET_COMPOSE_FILE"
require_file "$FLEET_TRANSPORT_COMPOSE_FILE"
require_file "$ANKAIOS_MANIFEST"

log "Starting Fleet Management services (Docker Compose)..."
docker compose \
  -f "$FLEET_COMPOSE_FILE" \
  -f "$FLEET_TRANSPORT_COMPOSE_FILE" \
  up --detach

log "Starting Ankaios control plane services as terminal calls (ank-server, ank-agent)..."

if command -v sudo >/dev/null 2>&1; then
  sudo ank-server &
else
  ank-server &
fi

if command -v sudo >/dev/null 2>&1; then
  sudo ank-agent --insecure --name agent_B &
else
  ank-agent --insecure --name agent_B &
fi


log "Waiting ${ANKAIOS_START_WAIT_SECONDS}s for Ankaios startup..."
sleep "${ANKAIOS_START_WAIT_SECONDS}"

log "Logging into ghcr.io (podman login)..."
if command -v sudo >/dev/null 2>&1; then
  sudo podman login ghcr.io
else
  podman login ghcr.io
fi

log "Applying Ankaios workload manifest: ${ANKAIOS_MANIFEST}"
ank -k apply "$ANKAIOS_MANIFEST"

log "Fleet Management and Ankaios workloads started."
