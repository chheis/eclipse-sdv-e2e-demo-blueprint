# Fleet Analysis Backend (Jakarta EE 21)

This service provides a small Jakarta EE 21 backend to analyze Fleet Management telemetry and
return summary statistics for dashboards or alerts.

## Responsibilities

- Accepts fleet telemetry snapshots as JSON.
- Returns computed summary metrics (fleet size, average speed, battery SOC range, braking count).

## Build

```bash
mvn package
```

## Run (example with Payara Micro)

1. Download [Payara Micro 6](https://www.payara.fish/downloads/payara-platform-community-edition/).
2. Deploy the WAR:

```bash
java -jar payara-micro.jar --deploy target/fleet-analysis-backend.war --contextRoot /fleet-analysis
```

The API will be available at `http://localhost:8080/fleet-analysis/api`.

## API

### `POST /api/analysis/summary`

Request body (example):

```json
[
  {
    "vehicleId": "bike-001",
    "speedKph": 42.3,
    "batterySoc": 0.78,
    "brakeActive": false,
    "updatedAt": "2024-06-10T10:15:30Z"
  },
  {
    "vehicleId": "bike-002",
    "speedKph": 12.4,
    "batterySoc": 0.52,
    "brakeActive": true,
    "updatedAt": "2024-06-10T10:15:32Z"
  }
]
```

Response:

```json
{
  "vehicleCount": 2,
  "averageSpeedKph": 27.35,
  "minBatterySoc": 0.52,
  "maxBatterySoc": 0.78,
  "brakingVehicles": 1
}
```
