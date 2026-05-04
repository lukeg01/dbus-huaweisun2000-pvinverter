# Setup Guide — Mac (Apple Silicon, clean macOS)

Complete setup from a fresh macOS installation on Apple Silicon (M1/M2/M3/M4).
Covers the three-component development environment:

1. **Modbus simulator** — `sun2000_sim.py` (port 5020)
2. **Venus OS** — Docker container (port 8080 / 1883)
3. **Venus OS driver** — runs inside the Docker container

The `sun2000_tool.py` interactive CLI also works after step 3 alone
(no Docker needed).

---

## 1. Xcode Command Line Tools

Required for `git`, `make`, and the C compiler that Homebrew and some Python
packages need.

```bash
xcode-select --install
```

A dialog will appear. Click **Install** and wait (~5 minutes).
Verify:

```bash
xcode-select -p
# /Library/Developer/CommandLineTools
```

---

## 2. Homebrew

The standard macOS package manager.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After installation, follow the **"Next steps"** printed at the end —
on Apple Silicon you must add Homebrew to your PATH:

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

pymodbus 2.5.3 is compatible with Python 3.8–3.11.
Python 3.11 is recommended.

```bash
brew install python@3.11
```

Add to PATH (if brew doesn't do it automatically):

```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zprofile
source ~/.zprofile
```

Verify:

```bash
python3.11 --version
# Python 3.11.x
```

> **Note:** macOS ships its own Python 3 at `/usr/bin/python3`, but it is
> intentionally minimal and should not be used for development.

---

## 4. Git

Git is included with Xcode Command Line Tools (step 1).
Verify:

```bash
git --version
# git version 2.x.x
```

---

## 5. Get the code

```bash
mkdir -p ~/venus-dev
cd ~/venus-dev
git clone https://github.com/kcbam/dbus-huaweisun2000-pvinverter.git
```

Your working directory should now look like:

```
~/venus-dev/
├── dbus-huaweisun2000-pvinverter/   ← driver + register library
├── sun2000_sim.py                   ← Modbus simulator
├── sun2000_tool.py                  ← interactive CLI tool
├── setup_driver.sh
├── validate_driver.sh
└── requirements.txt
```

---

## 6. Python virtual environment

Create an isolated environment so project dependencies don't conflict with
system packages.

```bash
cd ~/venus-dev
python3.11 -m venv venv
source venv/bin/activate
```

Your prompt will change to show `(venv)`.
You must run `source venv/bin/activate` again in every new terminal session
before using the tools.

---

## 7. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs `pymodbus==2.5.3`. Verify:

```bash
python -c "import pymodbus; print(pymodbus.__version__)"
# 2.5.3
```

---

## 8. Test the interactive tool (no Docker needed)

The `sun2000_tool.py` CLI and `sun2000_sim.py` simulator can run entirely on
the Mac, without Docker.

### Terminal A — start the simulator

```bash
cd ~/venus-dev
source venv/bin/activate
python sun2000_sim.py
```

Expected output:

```
2026-xx-xx INFO: Huawei SUN2000-5KTL-L1 simulator gestart op 0.0.0.0:5020
2026-xx-xx INFO: V3 registermap | 4900W | 230V | 50Hz | 42C
```

### Terminal B — run the tool

```bash
cd ~/venus-dev
source venv/bin/activate
python sun2000_tool.py
```

At the connection prompt use:

| Field | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `5020` |
| Unit ID | `0` |
| Version | `V3` |

For a real inverter, replace `127.0.0.1` / `5020` with the inverter's IP
address and Modbus port (default `6607` for Wi-Fi dongle, `502` for direct
Ethernet).

---

## 9. Docker Desktop (for full Venus OS integration test)

Required only to run the Venus OS environment and test the driver against a
real D-Bus / MQTT stack.

1. Download **Docker Desktop for Mac (Apple Silicon)**
   from <https://www.docker.com/products/docker-desktop/>
2. Open the `.dmg`, drag Docker to Applications, launch it.
3. Wait for Docker to finish starting (whale icon in menu bar becomes steady).
4. Verify:

```bash
docker --version
# Docker version 29.x.x
```

---

## 10. Venus OS Docker environment

```bash
cd ~
git clone https://github.com/victronenergy/venus-docker.git
cd venus-docker
./run.sh -s z
```

`-s z` loads the "original demo mode recordings" simulation which provides a
minimal but functional Venus OS D-Bus environment.

Services started:

| Service | Address |
|---|---|
| Venus OS web UI | http://localhost:8080 |
| MQTT broker | localhost:1883 |
| D-Bus | inside the container |

Wait until the web UI loads before continuing.

---

## 11. mosquitto (MQTT client — optional)

Used by `validate_driver.sh` to verify MQTT data.

```bash
brew install mosquitto
```

Test the MQTT broker (Venus OS Docker must be running):

```bash
mosquitto_sub -h localhost -p 1883 -t "N/#" -v -C 5
```

---

## 12. Deploy and validate the driver

With the simulator (step 8) and Venus OS Docker (step 10) both running:

```bash
~/venus-dev/setup_driver.sh
```

This will:
- Install pymodbus inside the Docker container
- Copy the driver files into the container
- Configure Modbus connection settings on D-Bus
- Start the driver process

Then validate:

```bash
~/venus-dev/validate_driver.sh
```

Expected output:

```
--- 1. Driver process ---
OK: driver draait

--- 2. Driver logs ---
INFO - Static device data: {'SN': 'HV2340123456', 'ModelID': 344.0, ...}

--- 3. D-Bus registratie ---
OK: "com.victronenergy.pvinverter.sun2000"

--- 4. Modbus verbinding vanuit container ---
OK: ActivePower = 4900 W
OK: PhaseAVoltage = 230.0 V
OK: DeviceStatus = 0x200
```

---

## Summary — what runs where

```
Mac (your machine)
├── Terminal A:  python sun2000_sim.py          port 5020
├── Terminal B:  python sun2000_tool.py         (connects to 127.0.0.1:5020)
│
└── Docker container (Venus OS)
    ├── D-Bus, MQTT broker                      ports 8080, 1883
    └── dbus-huaweisun2000-pvinverter           connects to host.docker.internal:5020
```

The driver inside Docker connects to the simulator on the Mac via the
`host.docker.internal` hostname that Docker Desktop provides automatically.

---

## Troubleshooting

**`xcode-select --install` says "already installed"**
You're good — CLT is present.

**`brew: command not found` after installation**
Run the `eval` line from step 2 again and restart your terminal.

**`python3.11: command not found`**
Check that `/opt/homebrew/opt/python@3.11/bin` is in your `$PATH`:
```bash
echo $PATH | tr ':' '\n' | grep python
```

**`pip install -r requirements.txt` fails with build errors**
Make sure Xcode CLT is installed (step 1), then retry.

**`python sun2000_sim.py` — "Address already in use"**
Another process is using port 5020. Find and stop it:
```bash
lsof -i :5020
kill <PID>
```

**`sun2000_tool.py` — "FAILED" on connect**
- Check the simulator is running (`lsof -i :5020`)
- Check the IP, port, and unit ID
- For a real inverter: verify the inverter's Modbus TCP is enabled in the
  Huawei app (Settings → Communication → Modbus TCP)

**Docker: "Cannot connect to the Docker daemon"**
Docker Desktop is not running. Open it from Applications and wait for the
whale icon to become steady in the menu bar.

**`setup_driver.sh` fails — "no such container"**
The Venus OS Docker container is not running. Execute step 10 first.
