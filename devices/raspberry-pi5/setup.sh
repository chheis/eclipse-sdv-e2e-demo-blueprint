#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  printf "[setup] %s\n" "$*"
}

log "Updating apt and installing packages..."
apt-get update
apt-get install -y can-utils net-tools curl vim podman

log "Disabling Wi-Fi power saving..."
NM_CONFIG="/etc/NetworkManager/conf.d/default-wifi-powersave-on.conf"
if [ ! -f "$NM_CONFIG" ]; then
  printf "[connection]\nwifi.powersave = 2\n" > "$NM_CONFIG"
else
  if grep -q "^[[:space:]]*wifi\\.powersave" "$NM_CONFIG"; then
    sed -i "s/^[[:space:]]*wifi\\.powersave.*/wifi.powersave = 2/" "$NM_CONFIG"
  else
    if ! grep -q "^[[:space:]]*\\[connection\\]" "$NM_CONFIG"; then
      printf "\n[connection]\n" >> "$NM_CONFIG"
    fi
    printf "wifi.powersave = 2\n" >> "$NM_CONFIG"
  fi
fi

if systemctl is-active --quiet NetworkManager; then
  systemctl reload NetworkManager || systemctl restart NetworkManager
fi

ANKAIOS_INSTALL_URL = "https://github.com/eclipse-ankaios/ankaios/releases/latest/download/install.sh"

if [ -n "${ANKAIOS_INSTALL_URL:-}" ]; then
  log "Installing Eclipse Ankaios from ${ANKAIOS_INSTALL_URL}..."
  curl -fsSL "$ANKAIOS_INSTALL_URL" | bash
else
  log "ANKAIOS_INSTALL_URL not set; skipping Ankaios install."
fi

log "Configuring SocketCAN (systemd-networkd)..."
install -D -m 0644 "${SCRIPT_DIR}/80-can.network" /etc/systemd/network/80-can.network
systemctl enable systemd-networkd
systemctl restart systemd-networkd

if [ "${PODMAN_LOGIN_GHCR:-0}" = "1" ]; then
  log "Logging into ghcr.io (podman login)..."
  podman login ghcr.io
fi

log "Setup complete."
