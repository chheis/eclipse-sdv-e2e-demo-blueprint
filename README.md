# eclipse-sdv-e2e-demo-blueprint

This repository prepares a Vehicle E/E Architecture demo that combines the **Fleet Management** use case from the Eclipse SDV Blueprints project with an in-vehicle **MotorBike Blinker** use case. The demo aligns all signal names to the COVESA Vehicle Signal Specification (VSS) and uses Kuksa Databroker 0.6.0 running as an Eclipse Ankaios 0.7.0 workload.

## Architecture overview

- **Raspberry Pi 4 (Connectivity Unit)**
  - Ubuntu
  - Eclipse Ankaios 0.7.0 (Podman workloads)
  - Kuksa Databroker 0.6.0
  - Kuksa CAN Provider + SocketCAN
  - Fleet Management Blueprint services
- **Raspberry Pi 5 (HCP)**
  - Optional higher-level control (Eclipse S-CORE or equivalent)
- **MCU1 LED Control (Arduino Uno + MCP2515)**
  - Controls 8-LED strip for left/right indicators and brake light
  - Publishes current light status over CAN @ 500 kbit/s
- **Driver input ECUs**
  - Arduino + joystick (manual input)
  - ThreadX board with buttons + OLED (status display)

## Device code folders

Each device has a dedicated folder under `devices/`:

- `devices/raspberry-pi4` - connectivity unit setup notes
- `devices/raspberry-pi5` - HCP/control node notes
- `devices/mcu1-led-control-can` - Arduino sketch for the LED strip
- `devices/backend-fleet-analysis-java` - Jakarta EE 21 backend for fleet analytics
- `devices/driver-input-ecu-arduino` - driver input ECU placeholder
- `devices/driver-input-ecu-threadx` - ThreadX input ECU placeholder

## VSS signals used

The blinker demo uses the following VSS signals:

- `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling`
- `Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling`
- `Vehicle.Body.Lights.Brake.IsActive`

The CAN encoding for these signals is documented in [`docs/vss-can-signals.md`](docs/vss-can-signals.md).

## References

- Fleet Management Blueprint: https://github.com/eclipse-sdv-blueprints/fleet-management
- Ankaios vehicle signals tutorial: https://eclipse-ankaios.github.io/ankaios/latest/usage/tutorial-vehicle-signals/
- Kuksa Databroker 0.6.0: https://github.com/eclipse-kuksa/kuksa-databroker/releases/tag/0.6.0
- Ankaios 0.7.0: https://github.com/eclipse-ankaios/ankaios/releases/tag/v0.7.0
- Kuksa CAN Provider: https://github.com/eclipse-kuksa/kuksa-can-provider
- MCP2515 Arduino library: https://github.com/107-systems/107-Arduino-MCP2515
