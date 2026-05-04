# Setup Guide — Mac (Apple Silicon, clean macOS)

Full development environment for the Huawei SUN2000 Venus OS driver on Apple Silicon.

Three components run together:

| Component | Where |
|---|---|
| **Modbus simulator** | Mac — `sun2000_sim.py` on port 5020 |
| **Venus OS** | Docker container (port 8080 web UI / port 1883 MQTT) |
| **Driver** | Inside the Docker container, connecting to the simulator |

`sun2000_tool.py` works without Docker — you only need steps 1–7.

---

## 1. Xcode Command Line Tools

```bash
xcode-select --install
```

A dialog will appear. Click **Install** and wait (~5 min).

Verify:

```bash
xcode-select -p
# /Library/Developer/CommandLineTools
```

---

## 2. Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the **"Next steps"** printed at the end — add Homebrew to PATH:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Verify:

```bash
brew --version
# Homebrew 5.x.x
```

---

## 3. Python 3.11

pymodbus 2.5.3 is compatible with Python 3.8–3.11. Python 3.11 is recommended.

```bash
brew install python@3.11
```

Add to PATH if Homebrew doesn't do it automatically:

```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:

```bash
python3.11 --version
# Python 3.11.x
```

> **Note:** macOS ships its own Python 3 at `/usr/bin/python3` but it is
> intentionally minimal — don't use it for development.

---

## 4. Get the code

```bash
git clone https://github.com/lukeg01/dbus-huaweisun2000-pvinverter.git
cd dbus-huaweisun2000-pvinverter
```

Your working directory should look like:

```
dbus-huaweisun2000-pvinverter/
├── dbus-huaweisun2000-pvinverter/   ← driver (installed on Venus OS)
├── sun2000_tool.py
├── sun2000_sim.py
├── setup_driver.sh
├── validate_driver.sh
├── requirements.txt
├── README.md
└── SETUP.md
```

---

## 5. Python virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

Your prompt will show `(venv)`.

> Run `source venv/bin/activate` again in every new terminal session before
> using the tool or simulator.

---

## 6. Install Python dependencies

```bash
pip install -r requirements.txt
```

Verify:

```bash
python -c "import pymodbus; print(pymodbus.__version__)"
# 2.5.3
```

---

## 7. Run the simulator and tool (no Docker needed)

The tool and simulator work standalone — useful for testing the tool against
a real or simulated inverter, without the full Venus OS environment.

**Terminal A — simulator:**

```bash
source venv/bin/activate
python sun2000_sim.py
```

Expected output:

```
INFO: Huawei SUN2000-5KTL-L1 simulator gestart op 0.0.0.0:5020
INFO: V3 registermap | 4900W | 230V | 50Hz | 42C
```

**Terminal B — tool:**

```bash
source venv/bin/activate
python sun2000_tool.py
```

At the connection prompt:

| Field | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `5020` |
| Unit ID | `0` |
| Version | `V3` |

Choose **option 1** — you should see all 115 registers with no errors.

---

## 8. Docker Desktop

Required for the Venus OS container.

1. Download **Docker Desktop for Mac (Apple Silicon)** from
   <https://www.docker.com/products/docker-desktop/>
2. Open the `.dmg`, drag Docker to Applications, launch it.
3. Wait until the whale icon in the menu bar is steady.

Verify:

```bash
docker --version
# Docker version 29.x.x
```

---

## 9. Venus OS Docker environment

```bash
cd ~
git clone https://github.com/victronenergy/venus-docker.git
cd venus-docker
./run.sh -s z
```

`-s z` loads the demo simulation (minimal functional Venus OS D-Bus stack).

Services started:

| Service | Address |
|---|---|
| Venus OS web UI | http://localhost:8080 |
| MQTT broker | localhost:1883 |

Wait until the web UI loads before continuing.

---

## 10. Deploy and start the driver

From the `dbus-huaweisun2000-pvinverter/` repo root:

```bash
source venv/bin/activate
python sun2000_sim.py &   # start simulator in background if not already running
./setup_driver.sh
```

`setup_driver.sh` does:
- Installs pymodbus inside the container
- Copies the driver into `/data/dbus-huaweisun2000-pvinverter/`
- Configures D-Bus settings (host `host.docker.internal`, port `5020`, unit `0`)
- Starts the driver process

Expected output ends with:

```
>>> Static data obtained: Model=SUN2000-5KTL-L1  SN=HV2340123456
>>> status changed to On-grid
com.victronenergy.pvinverter.sun2000
```

---

## 11. Validate

```bash
./validate_driver.sh
```

This checks:
1. Driver process is running
2. Driver logs show inverter data
3. D-Bus service `com.victronenergy.pvinverter.sun2000` is registered
4. Modbus connection from container → simulator works
5. MQTT topics publishing live values

All six checks should show **OK**.

---

## 12. Monitor MQTT data

```bash
mosquitto_sub -h localhost -p 1883 -t 'N/+/pvinverter/#' -v
```

You should see live updates for `/Ac/Power`, `/Ac/L1/Voltage`, `/StatusCode`, etc.
The `UpdateIndex` topic increments every ~5 seconds.

---

## Connecting to a real SUN2000 inverter

To test the tool against a physical inverter instead of the simulator:

### Enable Modbus TCP

Open the **Huawei FusionSolar** or **SUN2000** app:

> **Settings → Communication → Modbus TCP** → Enable

Some firmware versions label this **Settings → Communication parameters**.

### Connection parameters

| Parameter | Value | Notes |
|---|---|---|
| Host | inverter IP | e.g. `192.168.1.100` |
| Port | `6607` | SDongle (WLAN-FE / 4G) — most common |
| Port | `502` | Direct Ethernet on some models |
| Unit ID | `0` | Try `0` first |
| Unit ID | `1` | Use if unit `0` returns errors |
| Version | `V3` | Default; models post-2019 |
| Version | `V2` | Older models via SmartLogger |

> **One connection at a time:** some SDongle firmware versions reject a second
> TCP connection while the FusionSolar app is active. Close the app first.

```bash
python sun2000_tool.py
# Enter inverter IP, port 6607, unit 0, V3
# Option 1 — read all registers
```

---

## Troubleshooting

**`xcode-select --install` says "already installed"**
CLT is present — proceed.

**`brew: command not found` after installation**
Re-run the `eval` line from step 2 and restart your terminal.

**`python3.11: command not found`**
```bash
echo $PATH | tr ':' '\n' | grep python
```

**Docker container not found by `setup_driver.sh`**
Make sure Venus OS Docker is running (`docker ps` should show one container).

**Driver shows "FAILED" on Modbus connect**
- Check the simulator is running: `lsof -i :5020`
- The container reaches the Mac via `host.docker.internal` — verify with:
  `docker exec $(docker ps -q) python3 -c "import socket; socket.create_connection(('host.docker.internal', 5020))"`

**All registers return errors on V3**
Try version **V2** — the inverter may use the older register map.

**`/Ac/PowerLimit` not appearing on D-Bus**
Redeploy with `./setup_driver.sh` — the D-Bus path was added in v1.7.0.
