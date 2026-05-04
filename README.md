# dbus-huaweisun2000-pvinverter

Venus OS driver for Huawei SUN2000 inverters — D-Bus / MQTT integration for
Victron Cerbo GX and other Venus OS devices.

| Component | Description |
|---|---|
| `dbus-huaweisun2000-pvinverter/` | Venus OS driver (D-Bus service) |
| `sun2000_tool.py` | Interactive CLI — read registers or write power limit |
| `sun2000_sim.py` | Local Modbus TCP simulator (SUN2000-5KTL-L1, port 5020) |

---

## Driver features

- Reads inverter data via Modbus TCP and publishes to Venus OS D-Bus / MQTT
- Register map versions V1, V2, V3 (auto-detected or configurable)
- Supports single-phase and three-phase models
- Configurable via Venus OS GUI (*Settings → PV inverters → Huawei SUN2000*) or `override_config.py`
- `/Ac/PowerLimit` D-Bus path: ESS zero feed-in writes a watt value, the driver converts it to register 40125 (`ActivePowerPercentageDerating`) — same mechanism as Victron uses for Fronius
- 60-second watchdog on power limit: resets to 100% if ESS stops sending updates

### D-Bus paths published

| Path | Description |
|---|---|
| `/Ac/Power` | Active power (W) |
| `/Ac/L1/Power` | Phase A power (W) |
| `/Ac/L1/Voltage` | Phase A voltage (V) |
| `/Ac/L1/Current` | Phase A current (A) |
| `/Ac/Energy/Forward` | Daily energy yield (kWh) |
| `/Ac/PowerLimit` | Write: set active power limit (W); read: current limit |
| `/StatusCode` | Device status (On-grid, Standby, …) |
| `/DeviceInstance` | Venus OS device instance |

---

## Install on a real Cerbo GX / Venus OS device

```bash
wget -qO- https://raw.githubusercontent.com/lukeg01/dbus-huaweisun2000-pvinverter/main/dbus-huaweisun2000-pvinverter/setup/install_or_update.sh | bash
```

Configure via the Remote Console: **Settings → PV inverters → Huawei SUN2000**
(set Modbus host, port, unit ID, register version).

For manual settings override create `override_config.py` in the driver directory
(copy from `example_override_config.py`).

---

## Development setup (Mac + Venus OS Docker + simulator)

See [SETUP.md](SETUP.md) for the full step-by-step guide.

The three-component environment:

```
[sun2000_sim.py]  ←Modbus TCP port 5020→  [Venus OS Docker container]
                                                    ↑ driver inside
[sun2000_tool.py] ←Modbus TCP port 5020→  (same simulator)
```

Quick start once the environment is configured:

```bash
# Terminal 1 — simulator
source venv/bin/activate
python sun2000_sim.py

# Terminal 2 — deploy driver into Venus OS Docker container
./setup_driver.sh

# Terminal 3 — validate
./validate_driver.sh

# Terminal 4 — interactive tool (optional)
source venv/bin/activate
python sun2000_tool.py   # host: 127.0.0.1  port: 5020  unit: 0  version: V3
```

---

## sun2000_tool.py

Connects to a real inverter or the simulator and lets you:

1. **Read all registers** — prints a table of all V1/V2/V3 register values
2. **Write power limit** — accepts watts, percentage, or `none` (reset to 100%)
3. **Reconnect** — re-establish the connection without restarting

The standalone tool is also available separately at
[SUN2000-modbus-TCP-tool-and-sim](https://github.com/lukeg01/SUN2000-modbus-TCP-tool-and-sim).

---

## sun2000_sim.py

Simulates a SUN2000-5KTL-L1 on `0.0.0.0:5020`.

```bash
python sun2000_sim.py
```

Simulated state: 5 kW rated, 4.9 kW active, 230 V / 50 Hz / 42 °C.
Responds to register 40125 writes (power limit) and commands on 40200/40201 (on/off).

---

## Register map versions

| Version | Models |
|---|---|
| **V3** | SUN2000-xKTL-L1, -M1, -M2, -M3 — most models post-2019, Modbus TCP direct |
| **V2** | Older KTL-M0, models without suffix, connected via SmartLogger |
| **V1** | Legacy — not yet implemented |

---

## Debugging on Venus OS

```bash
# Check service status
svstat /service/dbus-huaweisun2000-pvinverter

# Stop / start / restart
svc -d /service/dbus-huaweisun2000-pvinverter
svc -u /service/dbus-huaweisun2000-pvinverter
sh /data/dbus-huaweisun2000-pvinverter/restart.sh

# Live logs
tail -f /var/log/dbus-huaweisun2000/current | tai64nlocal

# Quick Modbus connectivity check
python /data/dbus-huaweisun2000-pvinverter/connector_modbus.py
```

---

## Credits

Driver by [kcbam](https://github.com/kcbam/dbus-huaweisun2000-pvinverter).
Register map based on a modified version of
[olivergregorius/sun2000_modbus](https://github.com/olivergregorius/sun2000_modbus).
Energy meter code by @ricpax.
Inspired by [dbus-fronius-smartmeter](https://github.com/RalfZim/venus.dbus-fronius-smartmeter)
and [velib_python](https://github.com/victronenergy/velib_python).
