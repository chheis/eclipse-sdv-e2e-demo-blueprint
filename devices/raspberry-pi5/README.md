# Raspberry Pi 5 (Connectivity Unit)

This node runs the Fleet Management Blueprint components plus the vehicle signal stack for the MotorBike blinker demo.

## Required components

- **Ubuntu 24.04** image for Raspberry Pi 5
- **Eclipse Ankaios 0.7.0** running workloads with Podman
- **Eclipse Kuksa Databroker 0.6.0** workload
- **Eclipse Mosquitto** MQTT broker workload
- **MQTT-to-gRPC bridge** workload (for Kuksa Databroker)
- **SocketCAN** interface (e.g., `can0` at 500 kbit/s)
- **Kuksa CAN Provider** to translate CAN → VSS
- **Fleet Management Blueprint** services (as defined in the upstream repository)
- **Fleet Analysis Backend** (Jakarta EE) container

## Raspberry Pi5 config
- modify config.txt
- For the single CAN Hat add:
````
dtoverlay=mcp2515-can0,oscillator=12000000,interrupt=25,spimaxfrequency=2000000
````
- for the 10" display connect the HDMI and USB for power supply
- disable the network energy saving mode
````/etc/NetworkManager/conf.d/default-wifi-powersave-on.conf````
and set wifi.powersave to 2 (disabled) instead of 3 (enabled)
- install can-utils ````sudo apt-get install can-utils````
- install net-tools ````sudo apt install net-tools ````
- install curl ````sudo apt-get install curl````
- install vim ````sudo apt-get install vim````
- install eclipse ankaios (with script)
- install podman
  - podman login to ghcr.io (if private packages needed)
- enable socketCAN with startup (use /etc/systemd/network/80-can.network)
  - ````sudo vim /etc/systemd/network/80-can.network````
  - ````sudo systemctl enable systemd-networkd````
  - ````sudo systemctl restart systemd-networkd````

## Signal mapping

Use the VSS mapping defined in [`docs/vss-can-signals.md`](../../docs/vss-can-signals.md) to wire the CAN provider to the Arduino blinker ECU.

## Ankaios workload (Mosquitto + MQTT bridge + Kuksa Databroker + CAN provider)

Use the example Ankaios manifest in `devices/raspberry-pi5/ankaios/vehicle-signals.yaml`. It defines the Mosquitto MQTT broker, MQTT-to-gRPC bridge, Kuksa Databroker, and the Kuksa CAN Provider containers as Podman workloads.

1. Copy `devices/raspberry-pi5/ankaios/vehicle-signals.yaml` into your Ankaios manifests directory.
2. All those are currently embedded in the yaml (TODO: refactoring)
   1. Place VSS metadata at `/opt/kuksa/vss/vss.json` on the Raspberry Pi 5.
   2. Copy `devices/raspberry-pi5/ankaios/can-provider-config.json` to `/opt/kuksa/can-provider/can-provider-config.json` and adjust:
      - `can.interface` to your SocketCAN device (default: `can0`)
      - `signals` if you change the CAN IDs or VSS paths
   3. Build the MQTT-to-gRPC bridge image from `devices/raspberry-pi5/grpc-mqtt-bridge` and tag it as `grpc-mqtt-bridge:latest`.
   4. Copy `devices/raspberry-pi5/ankaios/grpc-mqtt.yaml` to `/opt/grpc-mqtt/grpc-mqtt.yaml` and point it at `localhost:1883` (MQTT) and `localhost:55555` (Kuksa Databroker gRPC).

The template config marks all signals as TX-only so the provider only writes CAN frames (no CAN read-back). If your kuksa-can-provider version uses a different key/value for transmit-only mappings, update the `direction` field accordingly.

The manifest uses host networking so the CAN provider can reach the databroker at `localhost:55555`, the MQTT bridge can reach Mosquitto at `localhost:1883`, and Mosquitto listens on `localhost:1883`. Point Arduino MQTT broker IPs to the Raspberry Pi 5 address (default in `mcu2-joystick-input.ino` and `driver-input-ecu-door.ino` is `192.168.88.100`).

## Build the MQTT bridge image

Build locally on the Raspberry Pi 5 (Podman):

```bash
podman build -t grpc-mqtt-bridge:latest devices/raspberry-pi5/grpc-mqtt-bridge
```

Build locally on a dev machine (Docker):

```bash
docker build -t grpc-mqtt-bridge:latest devices/raspberry-pi5/grpc-mqtt-bridge
```

The GitHub Actions workflow publishes the image to `ghcr.io/<owner>/<repo>/grpc-mqtt-bridge` on pushes to `main` and version tags.

## MQTT to Kuksa mappings

The joystick ECU and RFID door ECU publish JSON payloads on `InVehicleTopics`.

Example joystick payload:

```json
{
  "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling": true,
  "Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling": false,
  "Vehicle.Body.Lights.Brake.IsActive": "ACTIVE"
}
```

Example RFID payload:

```json
{
  "Vehicle.Driver.Identifier.Subject": "A1B2C3D4"
}
```

The sample bridge config (`devices/raspberry-pi5/ankaios/grpc-mqtt.yaml`) maps these JSON keys to Kuksa `Val/Set` updates.

## Communication workflow diagram

PlantUML source: `devices/raspberry-pi5/communication-workflow.puml`

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
