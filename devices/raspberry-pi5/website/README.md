# Raspberry Pi 5 Interactive Demo Website

This folder contains an interactive website for live audience explanations on the Raspberry Pi 5 display.

## What is implemented

The website has three views:

1. **Architecture**
   - Graphical component map inspired by [full-architecture.puml](../../../docs/full-architecture.puml).
   - Uses [demostrator-bg.png](../../../docs/demostrator-bg.png) as the visual background.
   - Live connection lines are highlighted when active.

2. **Signal Flow**
   - Live workflow lanes based on [communication-workflow.puml](../communication-workflow.puml).
   - Shows activity state for:
     - MQTT transfer
     - Databroker signal path
     - CAN feedback path
     - FMS pipeline
     - Ankaios workload management path
     - Dozzle monitoring path

3. **Dashboards**
   - Status cards for MQTT, Kuksa Databroker, Ankaios, and Dozzle.
   - Embedded iframes for Ankaios dashboard and Dozzle.
   - Running container table (Podman + Docker).

## Folder content

- `index.html`: UI layout
- `styles.css`: styling + animations
- `app.js`: live polling + rendering logic
- `api_server.py`: local API server + static host
- `Dockerfile`: container image for the website server
- `requirements.txt`: Python dependencies for container/runtime
- `site-config.json.example`: endpoint/container matching template

## Run with Ankaios (recommended)

The Ankaios manifest `devices/raspberry-pi5/ankaios/vehicle-signals.yaml` includes a `pi5-demo-website` workload that runs this website on port `8090`.

Build the container image locally on Pi5:

```bash
podman build -t localhost/pi5-demo-website:latest devices/raspberry-pi5/website
```

Apply manifest:

```bash
ank -k apply devices/raspberry-pi5/ankaios/vehicle-signals.yaml
```

Open:

```text
http://<pi5-ip>:8090
```

## Run standalone on Raspberry Pi 5

1. Go to the website folder:

```bash
cd devices/raspberry-pi5/website
```

2. Create local config (optional but recommended):

```bash
cp site-config.json.example site-config.json
```

3. Adjust `site-config.json` values for your environment:
   - `mqtt.host` / `mqtt.port`
   - `kuksa.host` / `kuksa.port`
   - `ankaios_dashboard_url`
   - `dozzle_url`
   - container name patterns under `containers`

4. Start the website server:

```bash
python3 api_server.py --host 0.0.0.0 --port 8090
```

5. Open in browser:

```text
http://<pi5-ip>:8090
```

## How live status is detected

The backend (`api_server.py`) polls:

- TCP reachability
  - MQTT broker (`host:1883` by default)
  - Kuksa Databroker (`host:55555` by default)
- HTTP reachability
  - Ankaios dashboard URL
  - Dozzle URL
- Container runtime state
  - `podman ps`
  - `docker ps`
- Optional recent activity hints from logs
  - `podman logs` / `docker logs` for bridge and databroker containers
- Optional direct signal observation via Kuksa Python client
  - reads configured VSS paths from Databroker (`kuksa_observer` in `site-config.json`)
  - marks command/feedback flows active when signal changes are observed
- Optional Ankaios workload query
  - attempts `ank` CLI commands (version-dependent)

The UI marks each path as:
- **Active**: endpoints are up and traffic hints are found
- **Reachable, idle**: endpoints are up but no recent traffic hints
- **Inactive**: endpoint/container path is not currently reachable

## Notes

- If `/api/status` is unreachable, the frontend switches to a simulated fallback mode so the page still demonstrates the UI behavior.
- If iframe embedding is blocked by remote headers (`X-Frame-Options`/`CSP`), use the "Open in new tab" links.
