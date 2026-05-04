# Huawei SUN2000 Venus OS Development Environment

Interactive tools and simulator for the
[dbus-huaweisun2000-pvinverter](./dbus-huaweisun2000-pvinverter) Venus OS driver.

---

## Contents

| File | Description |
|---|---|
| `sun2000_tool.py` | Interactive CLI — read registers or write power limit |
| `sun2000_sim.py` | Modbus TCP simulator (SUN2000-5KTL-L1, port 5020) |
| `setup_driver.sh` | Deploy and start the driver inside the Venus OS Docker container |
| `validate_driver.sh` | Validate driver process, D-Bus registration, and Modbus data |
| `requirements.txt` | Python dependencies |

---

## Setup

```bash
cd ~/venus-dev
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## sun2000_tool.py — Interactive Register Tool

Connect to a real SUN2000 inverter (or the local simulator) and interactively
read all known registers or write the active power limit.

### Quick start

```bash
cd ~/venus-dev
source venv/bin/activate
python sun2000_tool.py
```

The tool prompts for connection details on startup:

```
  Inverter host / IP [192.168.200.1]:
  Modbus TCP port [502]:
  Modbus unit ID [0]:
  Register version (V1 / V2 / V3) [V3]:
```

For the local simulator use `127.0.0.1`, port `5020`, unit `0`, version `V3`.

### Menu options

#### 1 — Read all registers

Reads every register defined in the selected `InverterRegisterV3` (or V1/V2)
register map and prints a formatted table:

```
  Name                                           Addr   Value                          Unit      Access
────────────────────────────────────────────────────────────────────────────────────────────────────────
  Model                                         30000   SUN2000-5KTL-L1                          RO
  SN                                            30015   HV2340123456                             RO
  ModelID                                       30070   344                                      RO
  RatedPower                                    30073   5000                           W         RO
  MaximumActivePower                            30075   5000                           W         RO
  ActivePower                                   32080   4900                           W         RO
  DeviceStatus                                  32089   On-grid                                  RO
  ActivePowerPercentageDerating                 40125   100                            %         RW
  ...
```

Write-only registers (`WO`) and multi-word curve registers (`MULTIDATA`) are
listed but not read.

#### 2 — Write power limit (register 40125)

Writes `ActivePowerPercentageDerating` (register 40125, gain /10, range 0–1000)
which is the Huawei register used by Victron ESS for zero feed-in / power
limiting.

Input is accepted in three formats:

| Input | Meaning | Register value written |
|---|---|---|
| `2500` | 2500 W (needs rated power to convert) | `500` (50.0%) |
| `75%` | 75 % of rated power | `750` (75.0%) |
| `none` | Remove limit, full output | `1000` (100.0%) |
| `0` | Zero output (soft stop) | `0` (0.0%) |

The tool reads `MaximumActivePower` from the inverter automatically for the
W → % conversion. If that fails it asks for the rated power.

A read-back after the write confirms the value was accepted.

#### 3 — Reconnect

Re-establishes the Modbus TCP connection without restarting the tool.
Useful if the inverter rebooted or the network was interrupted.

---

## sun2000_sim.py — Local Modbus Simulator

Simulates a SUN2000-5KTL-L1 on `0.0.0.0:5020` using the V3 register map.

```bash
source venv/bin/activate
python sun2000_sim.py
```

Simulated inverter state:

| Parameter | Value |
|---|---|
| Model | SUN2000-5KTL-L1 |
| Serial | HV2340123456 |
| Rated power | 5000 W |
| Active power | 4900 W |
| Phase A voltage | 230 V |
| Grid frequency | 50 Hz |
| Temperature | 42 °C |

The simulator responds to writes on register 40125 (power limit) and
registers 40200/40201 (startup/shutdown commands) and updates related
registers accordingly.

---

## Three-component test environment

To run the full Venus OS integration test:

**Terminal 1 — Venus OS Docker:**
```bash
cd ~/venus-docker
./run.sh -s z
```

**Terminal 2 — Modbus simulator:**
```bash
cd ~/venus-dev
source venv/bin/activate
python sun2000_sim.py
```

**Terminal 3 — Driver + validation:**
```bash
~/venus-dev/setup_driver.sh
~/venus-dev/validate_driver.sh
```

---

## Register map versions

| Version | Models |
|---|---|
| V3 | SUN2000-xKTL-L1, -M1, -M2, -M3 (most modern single- and three-phase) |
| V2 | Older KTL-M0, some L1 via SmartLogger (Modbus RTU) |
| V1 | Legacy (limited support) |

When connecting to a real inverter and unsure of the version, start with V3.
If registers come back as errors, try V2.

