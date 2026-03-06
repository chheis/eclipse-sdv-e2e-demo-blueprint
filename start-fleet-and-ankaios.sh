#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FLEET_COMPOSE_FILE="${FLEET_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose.yaml}"
FLEET_TRANSPORT_COMPOSE_FILE="${FLEET_TRANSPORT_COMPOSE_FILE:-${SCRIPT_DIR}/external/fleet-management/fms-blueprint-compose-zenoh.yaml}"
ANKAIOS_MANIFEST="${ANKAIOS_MANIFEST:-${SCRIPT_DIR}/devices/raspberry-pi5/ankaios/vehicle-signals.yaml}"
ANKAIOS_START_WAIT_SECONDS="${ANKAIOS_START_WAIT_SECONDS:-2}"
DOZZLE_ENABLED="${DOZZLE_ENABLED:-true}"
DOZZLE_IMAGE="${DOZZLE_IMAGE:-amir20/dozzle:latest}"
DOZZLE_CONTAINER_NAME="${DOZZLE_CONTAINER_NAME:-dozzle}"
DOZZLE_PORT="${DOZZLE_PORT:-8080}"
DOZZLE_DOCKER_SOCKET="${DOZZLE_DOCKER_SOCKET:-/var/run/docker.sock}"
WEBSITE_ENABLED="${WEBSITE_ENABLED:-true}"
WEBSITE_SERVER_SCRIPT="${WEBSITE_SERVER_SCRIPT:-${SCRIPT_DIR}/devices/raspberry-pi5/website/api_server.py}"
WEBSITE_HOST="${WEBSITE_HOST:-0.0.0.0}"
WEBSITE_PORT="${WEBSITE_PORT:-8090}"
WEBSITE_PID_FILE="${WEBSITE_PID_FILE:-/tmp/ee-demo-website-server.pid}"
WEBSITE_LOG_FILE="${WEBSITE_LOG_FILE:-/tmp/ee-demo-website-server.log}"

log() {
  printf "[start] %s\n" "$*"
}

warn() {
  printf "[start] %s\n" "$*" >&2
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

start_dozzle_container() {
  if [ "${DOZZLE_ENABLED}" != "true" ]; then
    log "Dozzle disabled via DOZZLE_ENABLED=${DOZZLE_ENABLED}."
    return
  fi

  if [ ! -S "${DOZZLE_DOCKER_SOCKET}" ]; then
    warn "Docker socket not found at ${DOZZLE_DOCKER_SOCKET}. Skipping Dozzle startup."
    return
  fi

  if docker ps --format '{{.Names}}' | grep -Fxq "${DOZZLE_CONTAINER_NAME}"; then
    log "Dozzle container '${DOZZLE_CONTAINER_NAME}' is already running."
    return
  fi

  if docker ps -a --format '{{.Names}}' | grep -Fxq "${DOZZLE_CONTAINER_NAME}"; then
    log "Starting existing Dozzle container '${DOZZLE_CONTAINER_NAME}'..."
    docker start "${DOZZLE_CONTAINER_NAME}" >/dev/null
    log "Dozzle available at: http://<host>:${DOZZLE_PORT}"
    return
  fi

  log "Starting Dozzle container '${DOZZLE_CONTAINER_NAME}' on port ${DOZZLE_PORT}..."
  if docker run -d \
    --name "${DOZZLE_CONTAINER_NAME}" \
    --restart unless-stopped \
    -p "${DOZZLE_PORT}:8080" \
    -v "${DOZZLE_DOCKER_SOCKET}:/var/run/docker.sock:ro" \
    "${DOZZLE_IMAGE}" >/dev/null; then
    log "Dozzle available at: http://<host>:${DOZZLE_PORT}"
  else
    warn "Dozzle startup failed. Continuing without Dozzle."
  fi
}

find_python_cmd() {
  if command -v python3 >/dev/null 2>&1; then
    printf "python3"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    printf "python"
    return
  fi
  return 1
}

start_website_server() {
  local python_cmd
  local website_pid

  if [ "${WEBSITE_ENABLED}" != "true" ]; then
    log "Website server disabled via WEBSITE_ENABLED=${WEBSITE_ENABLED}."
    return
  fi

  if [ ! -f "${WEBSITE_SERVER_SCRIPT}" ]; then
    warn "Website server script not found: ${WEBSITE_SERVER_SCRIPT}. Skipping website startup."
    return
  fi

  if ! python_cmd="$(find_python_cmd)"; then
    warn "python3/python not found. Skipping website startup."
    return
  fi

  if [ -f "${WEBSITE_PID_FILE}" ]; then
    website_pid="$(cat "${WEBSITE_PID_FILE}" 2>/dev/null || true)"
    if [ -n "${website_pid}" ] && kill -0 "${website_pid}" >/dev/null 2>&1; then
      log "Website server already running (pid ${website_pid})."
      return
    fi
    rm -f "${WEBSITE_PID_FILE}"
  fi

  if pgrep -f "${WEBSITE_SERVER_SCRIPT}" >/dev/null 2>&1; then
    log "Website server already running (process match on ${WEBSITE_SERVER_SCRIPT})."
    return
  fi

  log "Starting website server on ${WEBSITE_HOST}:${WEBSITE_PORT}..."
  if nohup "${python_cmd}" "${WEBSITE_SERVER_SCRIPT}" \
      --host "${WEBSITE_HOST}" \
      --port "${WEBSITE_PORT}" >>"${WEBSITE_LOG_FILE}" 2>&1 & then
    website_pid=$!
    printf "%s\n" "${website_pid}" > "${WEBSITE_PID_FILE}"
    log "Website available at: http://<host>:${WEBSITE_PORT}"
  else
    warn "Website server startup failed. Check log: ${WEBSITE_LOG_FILE}"
  fi
}

log "Starting Fleet Management services (Docker Compose)..."
docker compose \
  -f "$FLEET_COMPOSE_FILE" \
  -f "$FLEET_TRANSPORT_COMPOSE_FILE" \
  up --detach

start_dozzle_container

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

start_website_server

log "Fleet Management and Ankaios workloads started."
