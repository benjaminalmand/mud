# Applehill MUD Prototype

Local single-player MUD prototype built in Python with ANSI/VT100 terminal rendering.

## Run

```powershell
python main.py
```

The startup flow now uses accounts:

- log in with account name + password
- play a character on that account
- create a new character on that account
- delete characters from that account
- change the account password

## Run As A Network MUD

```powershell
python server_main.py --host 0.0.0.0 --port 4000
```

Clients can then connect with the VM's external IP and port `4000`.

## Deploy On Linux With systemd

The repo includes a service template at `deploy/applehill-mud.service`.
It stores live accounts and character saves outside the repo at:

- `/home/benjaminalmand/applehill-data/accounts`
- `/home/benjaminalmand/applehill-data/saves`

That keeps deploys and git pulls from wiping live players.

Typical install steps on the VM:

```bash
sudo cp deploy/applehill-mud.service /etc/systemd/system/applehill-mud.service
sudo systemctl daemon-reload
sudo systemctl enable applehill-mud
sudo systemctl start applehill-mud
sudo systemctl status applehill-mud
```

If you already have saves in the repo-local `saves/` folder on the VM, migrate them once:

```bash
mkdir -p /home/benjaminalmand/applehill-data/saves
mkdir -p /home/benjaminalmand/applehill-data/accounts
cp ~/mud/saves/*.json /home/benjaminalmand/applehill-data/saves/
sudo systemctl restart applehill-mud
```

## Current Features

- JSON-driven world data
- Classic MUD movement commands
- Room descriptions, items, NPCs, and monster presence
- Top-right directional minimap
- Simple inventory and dialogue
