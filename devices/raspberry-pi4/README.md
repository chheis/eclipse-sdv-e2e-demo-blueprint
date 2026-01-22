# Raspberry Pi 4 (Connectivity Unit)

This node runs the Fleet Management Blueprint components plus the vehicle signal stack for the MotorBike blinker demo.

## Required components

- **Ubuntu** image for Raspberry Pi 4
- **Eclipse Ankaios 0.7.0** running workloads with Podman
- **Eclipse Kuksa Databroker 0.6.0** workload
- **Eclipse Mosquitto** MQTT broker workload
- **SocketCAN** interface (e.g., `can0` at 500 kbit/s)
- **Kuksa CAN Provider** to translate CAN → VSS
- **Fleet Management Blueprint** services (as defined in the upstream repository)

## Signal mapping

Use the VSS mapping defined in [`docs/vss-can-signals.md`](../../docs/vss-can-signals.md) to wire the CAN provider to the Arduino blinker ECU.

## Ankaios workload (Mosquitto + Kuksa Databroker + CAN provider)

Use the example Ankaios manifest in `devices/raspberry-pi4/ankaios/vehicle-signals.yaml`. It defines the Mosquitto MQTT broker, Kuksa Databroker, and the Kuksa CAN Provider containers as Podman workloads.

1. Copy `devices/raspberry-pi4/ankaios/vehicle-signals.yaml` into your Ankaios manifests directory.
2. Place VSS metadata at `/opt/kuksa/vss/vss.json` on the Raspberry Pi 4.
3. Copy `devices/raspberry-pi4/ankaios/can-provider-config.json` to `/opt/kuksa/can-provider/can-provider-config.json` and adjust:
   - `can.interface` to your SocketCAN device (default: `can0`)
   - `signals` if you change the CAN IDs or VSS paths

The template config marks all signals as TX-only so the provider only writes CAN frames (no CAN read-back). If your kuksa-can-provider version uses a different key/value for transmit-only mappings, update the `direction` field accordingly.

The manifest uses host networking so the CAN provider can reach the databroker at `localhost:55555`, and Mosquitto listens on `localhost:1883`. Point the Arduino broker IP to the Raspberry Pi 4 address (default in `mcu2-joystick-input.ino` is `192.168.0.100`).

## Helpful upstream references

- Fleet Management Blueprint: https://github.com/eclipse-sdv-blueprints/fleet-management
- Ankaios vehicle signals tutorial: https://eclipse-ankaios.github.io/ankaios/latest/usage/tutorial-vehicle-signals/
- Kuksa Databroker 0.6.0: https://github.com/eclipse-kuksa/kuksa-databroker/releases/tag/0.6.0
- Ankaios 0.7.0: https://github.com/eclipse-ankaios/ankaios/releases/tag/v0.7.0
- Kuksa CAN Provider: https://github.com/eclipse-kuksa/kuksa-can-provider
