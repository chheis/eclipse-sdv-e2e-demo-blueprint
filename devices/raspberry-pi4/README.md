# Raspberry Pi 4 (Connectivity Unit)

This node runs the Fleet Management Blueprint components plus the vehicle signal stack for the MotorBike blinker demo.

## Required components

- **Ubuntu 24.04** image for Raspberry Pi 4
- **Eclipse Ankaios 0.7.0** running workloads with Podman
- **Eclipse Kuksa Databroker 0.6.0** workload
- **Eclipse Mosquitto** MQTT broker workload
- **MQTT-to-gRPC bridge** workload (for Kuksa Databroker)
- **SocketCAN** interface (e.g., `can0` at 500 kbit/s)
- **Kuksa CAN Provider** to translate CAN → VSS
- **Fleet Management Blueprint** services (as defined in the upstream repository)
- **Fleet Analysis Backend** (Jakarta EE) container

## Raspberry Pi4 config
- modify config.txt
- For the single CAN Hat add:
````
dtoverlay=mcp2515-can0,oscillator=12000000,interrupt=25,spimaxfrequency=2000000
````
for the SPI 7" display remove or comment out
````
dtoverlay=vc4-kms-v3d
````

## Signal mapping

Use the VSS mapping defined in [`docs/vss-can-signals.md`](../../docs/vss-can-signals.md) to wire the CAN provider to the Arduino blinker ECU.

## Ankaios workload (Mosquitto + MQTT bridge + Kuksa Databroker + CAN provider)

Use the example Ankaios manifest in `devices/raspberry-pi4/ankaios/vehicle-signals.yaml`. It defines the Mosquitto MQTT broker, MQTT-to-gRPC bridge, Kuksa Databroker, and the Kuksa CAN Provider containers as Podman workloads.

1. Copy `devices/raspberry-pi4/ankaios/vehicle-signals.yaml` into your Ankaios manifests directory.
2. Place VSS metadata at `/opt/kuksa/vss/vss.json` on the Raspberry Pi 4.
3. Copy `devices/raspberry-pi4/ankaios/can-provider-config.json` to `/opt/kuksa/can-provider/can-provider-config.json` and adjust:
   - `can.interface` to your SocketCAN device (default: `can0`)
   - `signals` if you change the CAN IDs or VSS paths
4. Build the MQTT-to-gRPC bridge image from `devices/raspberry-pi4/grpc-mqtt-bridge` and tag it as `grpc-mqtt-bridge:latest`.
5. Copy `devices/raspberry-pi4/ankaios/grpc-mqtt.yaml` to `/opt/grpc-mqtt/grpc-mqtt.yaml` and point it at `localhost:1883` (MQTT) and `localhost:55555` (Kuksa Databroker gRPC).

The template config marks all signals as TX-only so the provider only writes CAN frames (no CAN read-back). If your kuksa-can-provider version uses a different key/value for transmit-only mappings, update the `direction` field accordingly.

The manifest uses host networking so the CAN provider can reach the databroker at `localhost:55555`, the MQTT bridge can reach Mosquitto at `localhost:1883`, and Mosquitto listens on `localhost:1883`. Point the Arduino broker IP to the Raspberry Pi 4 address (default in `mcu2-joystick-input.ino` is `192.168.0.100`).

## Build the MQTT bridge image

Build locally on the Raspberry Pi 4 (Podman):

```bash
podman build -t grpc-mqtt-bridge:latest devices/raspberry-pi4/grpc-mqtt-bridge
```

Build locally on a dev machine (Docker):

```bash
docker build -t grpc-mqtt-bridge:latest devices/raspberry-pi4/grpc-mqtt-bridge
```

The GitHub Actions workflow publishes the image to `ghcr.io/<owner>/<repo>/grpc-mqtt-bridge` on pushes to `main` and version tags.

## MQTT to Kuksa mappings

The joystick publishes a JSON payload on `InVehicleTopics` with these VSS keys:

```json
{
  "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling": true,
  "Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling": false,
  "Vehicle.Body.Lights.Brake.IsActive": false
}
```

The sample bridge config (`devices/raspberry-pi4/ankaios/grpc-mqtt.yaml`) maps each JSON key to a Kuksa `Val/Set` update so all three signals are set on every message.

## Communication workflow diagram

PlantUML source: `devices/raspberry-pi4/communication-workflow.puml`

## Fleet Analysis Backend (runs on Pi 4)

The fleet analysis service runs alongside the Fleet Management Blueprint stack via Docker Compose and
connects to the same InfluxDB instance on the `fms-backend` network.

1. From `external/fleet-management`, start the stack:

```bash
docker compose -f ./fms-blueprint-compose.yaml -f ./fms-blueprint-compose-zenoh.yaml up --detach
```

2. The service will be available at `http://<pi4-ip>:8082/fleet-analysis/api`.

Configuration is done via environment variables:

- `INFLUXDB_STATS_INTERVAL_SECONDS` (default: 30)
- `INFLUXDB_URI` (default: http://influxdb:8086)
- `INFLUXDB_ORG` (default: sdv)
- `INFLUXDB_BUCKET` (default: demo)
- `INFLUXDB_TOKEN_FILE` (mounted from the InfluxDB init job)

## Helpful upstream references

- Fleet Management Blueprint: https://github.com/eclipse-sdv-blueprints/fleet-management
- Ankaios vehicle signals tutorial: https://eclipse-ankaios.github.io/ankaios/latest/usage/tutorial-vehicle-signals/
- Kuksa Databroker 0.6.0: https://github.com/eclipse-kuksa/kuksa-databroker/releases/tag/0.6.0
- Ankaios 0.7.0: https://github.com/eclipse-ankaios/ankaios/releases/tag/v0.7.0
- Kuksa CAN Provider: https://github.com/eclipse-kuksa/kuksa-can-provider
