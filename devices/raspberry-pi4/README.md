# Raspberry Pi 4 (Connectivity Unit)

This node runs the Fleet Management Blueprint components plus the vehicle signal stack for the MotorBike blinker demo.

## Required components

- **Ubuntu** image for Raspberry Pi 4
- **Eclipse Ankaios 0.7.0** running workloads with Podman
- **Eclipse Kuksa Databroker 0.6.0** workload
- **SocketCAN** interface (e.g., `can0` at 500 kbit/s)
- **Kuksa CAN Provider** to translate CAN → VSS
- **Fleet Management Blueprint** services (as defined in the upstream repository)

## Signal mapping

Use the VSS mapping defined in [`docs/vss-can-signals.md`](../../docs/vss-can-signals.md) to wire the CAN provider to the Arduino blinker ECU.

## Helpful upstream references

- Fleet Management Blueprint: https://github.com/eclipse-sdv-blueprints/fleet-management
- Ankaios vehicle signals tutorial: https://eclipse-ankaios.github.io/ankaios/latest/usage/tutorial-vehicle-signals/
- Kuksa Databroker 0.6.0: https://github.com/eclipse-kuksa/kuksa-databroker/releases/tag/0.6.0
- Ankaios 0.7.0: https://github.com/eclipse-ankaios/ankaios/releases/tag/v0.7.0
- Kuksa CAN Provider: https://github.com/eclipse-kuksa/kuksa-can-provider
