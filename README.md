# Applehill MUD Prototype

Local single-player MUD prototype built in Python with ANSI/VT100 terminal rendering.

## Run

```powershell
python main.py
```

## Run As A Network MUD

```powershell
python server_main.py --host 0.0.0.0 --port 4000
```

Clients can then connect with the VM's external IP and port `4000`.

## Deploy On Linux With systemd

The repo includes a service template at `deploy/applehill-mud.service`.

Typical install steps on the VM:

```bash
sudo cp deploy/applehill-mud.service /etc/systemd/system/applehill-mud.service
sudo systemctl daemon-reload
sudo systemctl enable applehill-mud
sudo systemctl start applehill-mud
sudo systemctl status applehill-mud
```

## Current Features

- JSON-driven world data
- Classic MUD movement commands
- Room descriptions, items, NPCs, and monster presence
- Top-right directional minimap
- Simple inventory and dialogue
