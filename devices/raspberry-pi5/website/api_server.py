#!/usr/bin/env python3
"""Lightweight status API + static host for the Raspberry Pi 5 demo website."""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
CONFIG_FILE = ROOT / "site-config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "probe_timeout_seconds": 1.2,
    "log_window_seconds": 45,
    "mqtt": {"host": "127.0.0.1", "port": 1883},
    "kuksa": {"host": "127.0.0.1", "port": 55555},
    "ankaios_dashboard_url": "http://127.0.0.1:8084",
    "dozzle_url": "http://127.0.0.1:8080",
    "containers": {
        "mqtt_broker": ["mosquitto", "mqtt"],
        "mqtt_bridge": ["grpc-mqtt-bridge", "mqtt-bridge"],
        "kuksa_databroker": ["kuksa-databroker", "databroker"],
        "can_provider": ["kuksa-can-provider", "can-provider"],
        "ankaios": ["ank-server", "ank-agent", "ankaios"],
        "dozzle": ["dozzle"],
        "fms_forwarder": ["fms-forwarder"],
        "grafana": ["grafana"],
    },
}


class StatusError(Exception):
    """Internal helper exception for status probing."""


def deep_merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict[str, Any]:
    cfg: dict[str, Any] = dict(DEFAULT_CONFIG)
    if CONFIG_FILE.exists():
        try:
            parsed = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                cfg = deep_merge(cfg, parsed)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def run_command(args: list[str], timeout_seconds: float = 4.0) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }


def probe_tcp(host: str, port: int, timeout_seconds: float) -> dict[str, Any]:
    try:
        sock = socket.create_connection((host, int(port)), timeout=timeout_seconds)
        sock.close()
        return {
            "active": True,
            "detail": f"TCP reachable at {host}:{port}",
        }
    except OSError as exc:
        return {
            "active": False,
            "detail": f"TCP unreachable at {host}:{port} ({exc})",
        }


def probe_http(url: str, timeout_seconds: float) -> dict[str, Any]:
    if not url:
        return {"active": False, "detail": "URL not configured", "status_code": None}

    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds) as response:
            code = getattr(response, "status", 200)
            return {
                "active": 200 <= code < 500,
                "status_code": code,
                "detail": f"HTTP {code}",
            }
    except HTTPError as exc:
        code = getattr(exc, "code", None)
        return {
            "active": code is not None and code < 500,
            "status_code": code,
            "detail": f"HTTP error {code}",
        }
    except URLError as exc:
        return {
            "active": False,
            "status_code": None,
            "detail": f"HTTP unreachable ({exc.reason})",
        }


def list_containers(runtime: str) -> list[dict[str, Any]]:
    if not shutil.which(runtime):
        return []

    result = run_command([runtime, "ps", "--format", "{{json .}}"])
    if not result["ok"]:
        return []

    containers: list[dict[str, Any]] = []
    for line in result["stdout"].splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue

        name = raw.get("Names") or raw.get("Name") or "unknown"
        image = raw.get("Image") or "unknown"
        container_id = raw.get("ID") or raw.get("Id") or ""
        state = raw.get("State") or ""
        status = raw.get("Status") or state or "unknown"

        containers.append(
            {
                "runtime": runtime,
                "id": container_id,
                "name": name,
                "image": image,
                "state": state or "running",
                "status": status,
            }
        )

    return containers


def find_matches(
    containers: list[dict[str, Any]],
    patterns: list[str],
) -> list[dict[str, Any]]:
    lowered = [p.lower() for p in patterns]
    matches: list[dict[str, Any]] = []
    for item in containers:
        haystack = f"{item['name']} {item['image']}".lower()
        if any(pattern in haystack for pattern in lowered):
            matches.append(item)
    return matches


def collect_recent_logs(
    container: dict[str, Any] | None,
    seconds_window: int,
) -> dict[str, Any]:
    if not container:
        return {"lines": None, "keyword_hits": None, "detail": "container not found"}

    runtime = container["runtime"]
    name = container["name"]
    result = run_command([runtime, "logs", "--since", f"{seconds_window}s", name], timeout_seconds=5)
    if not result["ok"]:
        return {
            "lines": None,
            "keyword_hits": None,
            "detail": f"{runtime} logs failed",
        }

    combined = f"{result['stdout']}\n{result['stderr']}".strip()
    if not combined:
        return {"lines": 0, "keyword_hits": 0, "detail": "no recent log lines"}

    lines = [entry for entry in combined.splitlines() if entry.strip()]
    keywords = (
        "mqtt",
        "topic",
        "set",
        "val",
        "vehicle.",
        "can",
        "signal",
        "update",
    )
    hits = sum(1 for line in lines if any(word in line.lower() for word in keywords))
    return {
        "lines": len(lines),
        "keyword_hits": hits,
        "detail": f"{len(lines)} lines in last {seconds_window}s",
    }


def try_query_ank_workloads() -> dict[str, Any]:
    if not shutil.which("ank"):
        return {
            "available": False,
            "workload_count": None,
            "detail": "ank CLI not found",
        }

    candidate_commands = [
        ["ank", "-k", "get", "workloads", "-o", "json"],
        ["ank", "-k", "get", "workload", "-o", "json"],
        ["ank", "get", "workloads", "-o", "json"],
        ["ank", "get", "workload", "-o", "json"],
    ]

    for cmd in candidate_commands:
        result = run_command(cmd, timeout_seconds=5)
        if not result["ok"]:
            continue
        payload = result["stdout"].strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, list):
            count = len(parsed)
        elif isinstance(parsed, dict):
            workloads = parsed.get("workloads")
            if isinstance(workloads, list):
                count = len(workloads)
            elif isinstance(workloads, dict):
                count = len(workloads.keys())
            else:
                count = 1
        else:
            count = None

        return {
            "available": True,
            "workload_count": count,
            "detail": "queried via ank CLI",
        }

    return {
        "available": False,
        "workload_count": None,
        "detail": "ank CLI query failed",
    }


def build_status(config: dict[str, Any]) -> dict[str, Any]:
    timeout = float(config.get("probe_timeout_seconds", 1.2))
    window = int(config.get("log_window_seconds", 45))

    mqtt = probe_tcp(config["mqtt"]["host"], int(config["mqtt"]["port"]), timeout)
    kuksa = probe_tcp(config["kuksa"]["host"], int(config["kuksa"]["port"]), timeout)
    ank_dashboard = probe_http(config.get("ankaios_dashboard_url", ""), timeout)
    dozzle = probe_http(config.get("dozzle_url", ""), timeout)

    containers = list_containers("podman") + list_containers("docker")
    container_patterns = config.get("containers", {})
    grouped: dict[str, list[dict[str, Any]]] = {}

    for key, patterns in container_patterns.items():
        if isinstance(patterns, list):
            grouped[key] = find_matches(containers, patterns)
        else:
            grouped[key] = []

    bridge_container = grouped.get("mqtt_bridge", [None])[0] if grouped.get("mqtt_bridge") else None
    databroker_container = (
        grouped.get("kuksa_databroker", [None])[0] if grouped.get("kuksa_databroker") else None
    )

    bridge_logs = collect_recent_logs(bridge_container, window)
    databroker_logs = collect_recent_logs(databroker_container, window)
    ank_cli = try_query_ank_workloads()

    mqtt_transfer_active = mqtt["active"] and bool(grouped.get("mqtt_bridge")) and bool(grouped.get("mqtt_broker"))
    databroker_signals_active = kuksa["active"] and bool(grouped.get("can_provider"))

    fms_active = bool(grouped.get("fms_forwarder")) and bool(grouped.get("grafana"))
    ankaios_active = bool(grouped.get("ankaios")) or bool(ank_dashboard["active"]) or bool(ank_cli["available"])
    dozzle_active = bool(grouped.get("dozzle")) or bool(dozzle["active"])

    return {
        "timestamp": utc_now_iso(),
        "services": {
            "mqtt": mqtt,
            "kuksa": kuksa,
            "ankaios_dashboard": ank_dashboard,
            "dozzle": dozzle,
        },
        "dashboards": {
            "ankaios": {
                "url": config.get("ankaios_dashboard_url", ""),
                "reachable": bool(ank_dashboard.get("active")),
            },
            "dozzle": {
                "url": config.get("dozzle_url", ""),
                "reachable": bool(dozzle.get("active")),
            },
        },
        "containers": {
            "running_count": len(containers),
            "running": containers,
            "groups": {
                name: [item["name"] for item in entries]
                for name, entries in grouped.items()
            },
        },
        "activity": {
            "bridge": bridge_logs,
            "databroker": databroker_logs,
            "ank_cli": ank_cli,
        },
        "connections": {
            "mqtt_transfer": {
                "active": mqtt_transfer_active,
                "traffic_detected": bool(bridge_logs.get("keyword_hits", 0)),
                "detail": "MQTT Broker -> Bridge -> Kuksa path",
            },
            "databroker_signals": {
                "active": databroker_signals_active,
                "traffic_detected": bool(databroker_logs.get("keyword_hits", 0)),
                "detail": "Kuksa Databroker <-> CAN Provider",
            },
            "can_feedback": {
                "active": databroker_signals_active,
                "traffic_detected": bool(databroker_logs.get("keyword_hits", 0)),
                "detail": "Blinker ECU status feedback to VSS",
            },
            "fms_pipeline": {
                "active": fms_active,
                "traffic_detected": fms_active,
                "detail": "Kuksa -> FMS Forwarder -> Grafana",
            },
            "ankaios_workloads": {
                "active": ankaios_active,
                "traffic_detected": ankaios_active,
                "detail": "Ankaios control plane and workloads",
            },
            "dozzle_monitoring": {
                "active": dozzle_active,
                "traffic_detected": dozzle_active,
                "detail": "Dozzle container monitor",
            },
        },
    }


class DemoHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler_class: type[SimpleHTTPRequestHandler]):
        super().__init__(server_address, handler_class)
        self.config = load_config()


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def send_json(self, payload: dict[str, Any], status_code: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            payload = build_status(self.server.config)  # type: ignore[attr-defined]
            self.send_json(payload)
            return

        if parsed.path == "/api/config":
            payload = self.server.config  # type: ignore[attr-defined]
            self.send_json(payload)
            return

        if parsed.path == "/api/health":
            self.send_json({"ok": True, "timestamp": utc_now_iso()})
            return

        if parsed.path in ("/", ""):
            self.path = "/index.html"

        super().do_GET()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Raspberry Pi5 demo website server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8090, help="Bind port (default: 8090)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = DemoHTTPServer((args.host, args.port), DemoHandler)

    print(f"Serving website from: {ROOT}")
    print(f"Open: http://{args.host}:{args.port}")
    print(f"API:  http://{args.host}:{args.port}/api/status")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
