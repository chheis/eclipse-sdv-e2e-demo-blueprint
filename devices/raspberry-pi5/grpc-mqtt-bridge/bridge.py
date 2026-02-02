import argparse
import json
import sys
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import yaml


def _parse_args():
    parser = argparse.ArgumentParser(description="MQTT to Kuksa gRPC bridge")
    parser.add_argument(
        "--config",
        required=True,
        help="Path to grpc-mqtt.yaml config file",
    )
    return parser.parse_args()


def _read_config(path):
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _parse_broker_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in ("mqtt", "tcp"):
        raise ValueError(f"Unsupported broker scheme: {parsed.scheme}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 1883
    return host, port


def _json_pointer(value, pointer):
    if pointer in ("", "/"):
        return value
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer: {pointer}")
    current = value
    for raw_part in pointer.split("/")[1:]:
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            index = int(part)
            current = current[index]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(pointer)
    return current


def _cast_value(value, value_type):
    if not value_type:
        return value
    value_type = value_type.lower()
    if value_type == "bool":
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "on"):
                return True
            if normalized in ("false", "0", "no", "off"):
                return False
        return bool(value)
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "string":
        return str(value)
    return value


class KuksaWriter:
    def __init__(self, host, port):
        self._datapoint_class = None
        self._client = self._build_client(host, port)
        self._connect()
        self._set_values = self._select_setter()

    def _build_client(self, host, port):
        try:
            from kuksa_client.grpc import Datapoint, VSSClient

            self._datapoint_class = Datapoint
            return VSSClient(host, port)
        except ImportError:
            from kuksa_client import KuksaClient

            return KuksaClient(host=host, port=port)

    def _connect(self):
        if hasattr(self._client, "connect"):
            self._client.connect()

    def _select_setter(self):
        if hasattr(self._client, "set_target_values"):
            return self._client.set_target_values
        if hasattr(self._client, "set_current_values"):
            return self._client.set_current_values
        raise RuntimeError("Kuksa client has no supported set_* method")

    def write(self, updates):
        if not updates:
            return
        self._set_values(self._normalize_updates(updates))

    def _normalize_updates(self, updates):
        if self._datapoint_class is None:
            return updates
        normalized = {}
        for path, value in updates.items():
            if hasattr(value, "v1_to_message"):
                normalized[path] = value
            else:
                normalized[path] = self._datapoint_class(value=value)
        return normalized


def main():
    args = _parse_args()
    config = _read_config(args.config)

    mqtt_config = config.get("mqtt", {})
    grpc_config = config.get("grpc", {})
    mappings = config.get("mappings", [])

    broker_url = mqtt_config.get("broker", "tcp://localhost:1883")
    broker_host, broker_port = _parse_broker_url(broker_url)
    client_id = mqtt_config.get("clientId", "kuksa-mqtt-bridge")
    subscriptions = mqtt_config.get("subscriptions", [])

    grpc_target = grpc_config.get("target", "localhost:55555")
    if ":" in grpc_target:
        grpc_host, grpc_port = grpc_target.rsplit(":", 1)
    else:
        grpc_host, grpc_port = grpc_target, "55555"

    try:
        grpc_port = int(grpc_port)
    except ValueError as exc:
        raise ValueError(f"Invalid gRPC port: {grpc_port}") from exc

    kuksa_writer = KuksaWriter(grpc_host, grpc_port)

    def on_message(_client, _userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except json.JSONDecodeError:
            print("Skipping non-JSON MQTT payload", file=sys.stderr)
            return

        updates = {}
        for mapping in mappings:
            mqtt_mapping = mapping.get("mqtt", {})
            if mqtt_mapping.get("topic") != msg.topic:
                continue
            mqtt_pointer = mqtt_mapping.get("jsonPointer", "/")
            try:
                scoped_payload = _json_pointer(payload, mqtt_pointer)
            except (KeyError, ValueError, IndexError):
                continue
            grpc_mapping = mapping.get("grpc", {})
            for update in grpc_mapping.get("updates", []):
                pointer = update.get("jsonPointer", "/")
                try:
                    value = _json_pointer(scoped_payload, pointer)
                except (KeyError, ValueError, IndexError):
                    continue
                try:
                    value = _cast_value(value, update.get("type"))
                except (TypeError, ValueError):
                    continue
                updates[update.get("path")] = value

        try:
            kuksa_writer.write(updates)
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to write to Kuksa: {exc}", file=sys.stderr)

    client = mqtt.Client(client_id=client_id)
    client.on_message = on_message
    client.connect(broker_host, broker_port)

    for subscription in subscriptions:
        topic = subscription.get("topic")
        if not topic:
            continue
        qos = subscription.get("qos", 0)
        client.subscribe(topic, qos=qos)

    client.loop_forever()


if __name__ == "__main__":
    main()
