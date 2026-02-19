#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FLEET_COMPOSE_FILE="${FLEET_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose.yaml}"
FLEET_TRANSPORT_COMPOSE_FILE="${FLEET_TRANSPORT_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose-zenoh.yaml}"

log() {
  printf "[shutdown] %s\n" "$*"
}

warn() {
  printf "[shutdown] %s\n" "$*" >&2
}

have_cmd() {
  command -v "$1" >/dev/null 2>&1
}

stop_fleet_compose() {
  if ! have_cmd docker; then
    warn "docker not found. Skipping Docker Compose shutdown."
    return
  fi

  if [ ! -f "$FLEET_COMPOSE_FILE" ] || [ ! -f "$FLEET_TRANSPORT_COMPOSE_FILE" ]; then
    warn "Compose file(s) missing. Skipping Docker Compose shutdown."
    return
  fi

  log "Stopping Fleet Management services (Docker Compose)..."
  docker compose \
    -f "$FLEET_COMPOSE_FILE" \
    -f "$FLEET_TRANSPORT_COMPOSE_FILE" \
    down --remove-orphans
}

stop_podman_containers() {
  if ! have_cmd podman; then
    warn "podman not found. Skipping Podman shutdown."
    return
  fi

  if [ -z "$(podman ps -q)" ]; then
    log "No running Podman containers found."
    return
  fi

  log "Stopping all running Podman containers..."
  podman stop -a
}

stop_ankaios_processes() {
  if have_cmd pkill; then
    if pgrep -f "ank-agent" >/dev/null 2>&1; then
      log "Stopping ank-agent process(es)..."
      pkill -f "ank-agent" || true
    fi

    if pgrep -f "ank-server" >/dev/null 2>&1; then
      log "Stopping ank-server process(es)..."
      pkill -f "ank-server" || true
    fi
  fi
}

stop_fleet_compose
stop_podman_containers
stop_ankaios_processes

log "Shutdown completed."
