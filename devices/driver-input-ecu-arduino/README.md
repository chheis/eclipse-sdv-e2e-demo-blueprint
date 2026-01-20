# Driver Input ECU (Arduino + Joystick)

This device represents a manual driver input ECU for the blinkers.

## Responsibilities

- Capture joystick input from an analog Joystick: https://docs.sunfounder.com/projects/elite-explorer-kit/de/latest/basic_projects/20_basic_joystick.html
- Publish VSS-aligned blinker requests to the Raspberry Pi 4 via Ethernet/Wi-Fi using Zenoh.
- Set target values:
  - `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling`
  - `Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling`
  - `Vehicle.Body.Lights.Brake.IsActive`

## Zenoh publishing details

The Arduino sketch publishes a JSON payload whenever the joystick state changes.

- Zenoh router endpoint: `tcp/<pi4-ip>:7447`
- Key expression: `Vehicle/Body/Lights/Signals`
- Update payload on every joystick change (left/right/brake).

Example payload:

```json
{
  "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling": true,
  "Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling": false,
  "Vehicle.Body.Lights.Brake.IsActive": false
}
```

## Status

Zenoh-based publishing implemented in the Arduino sketch.
