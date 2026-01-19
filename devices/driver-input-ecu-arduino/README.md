# Driver Input ECU (Arduino + Joystick)

This device represents a manual driver input ECU for the blinkers.

## Responsibilities

- Capture joystick or button input.
- Send VSS-aligned blinker requests to the Raspberry Pi 4 via Ethernet/Wi-Fi and gRPC to the Kuksa databroker.
- Set target values:
  - `Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling`
  - `Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling`
  - `Vehicle.Body.Lights.Brake.IsActive`

## gRPC publishing details

Use the Kuksa Databroker gRPC API on the Raspberry Pi 4 to publish joystick state.

- gRPC endpoint: `<pi4-ip>:55555`
- Service: `kuksa.val.v1.Val/Set`
- Update target values on every joystick change (left/right/brake).

Example (using `grpcurl` from a dev machine):

```bash
grpcurl -plaintext -d '{
  "updates": [
    {"entry": {"path": "Vehicle.Body.Lights.DirectionIndicator.Left.IsSignaling"}, "value": {"bool": true}},
    {"entry": {"path": "Vehicle.Body.Lights.DirectionIndicator.Right.IsSignaling"}, "value": {"bool": false}},
    {"entry": {"path": "Vehicle.Body.Lights.Brake.IsActive"}, "value": {"bool": false}}
  ]
}' <pi4-ip>:55555 kuksa.val.v1.Val/Set
```

## Status

Implementation placeholder for the demo architecture.
