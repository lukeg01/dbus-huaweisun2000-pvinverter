#!/usr/bin/env python3
"""
Interactive Modbus TCP CLI for Huawei SUN2000 inverters.

Features:
  1. Read all registers from the driver's register map (V1/V2/V3)
  2. Write the active power limit to register 40125
     (ActivePowerPercentageDerating — used by Victron ESS zero feed-in)

Run from the venus-dev directory with the project venv active:
    source venv/bin/activate
    python sun2000_tool.py
"""

import sys
import os
import logging

# ---------------------------------------------------------------------------
# Locate the driver package that lives next to this script
# ---------------------------------------------------------------------------
_DRIVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "dbus-huaweisun2000-pvinverter")
if not os.path.isdir(_DRIVER_DIR):
    sys.exit(f"ERROR: driver directory not found at {_DRIVER_DIR}")
if _DRIVER_DIR not in sys.path:
    sys.path.insert(0, _DRIVER_DIR)

from sun2000_modbus import inverter as inv_module          # noqa: E402
from sun2000_modbus import inverter_registers              # noqa: E402
from sun2000_modbus.registers import AccessType            # noqa: E402
from sun2000_modbus import datatypes                       # noqa: E402

POWER_LIMIT_REGISTER = 40125


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def _hr(char="─", width=92):
    print(char * width)


def _prompt(label, default=None):
    hint = f" [{default}]" if default is not None else ""
    try:
        raw = input(f"  {label}{hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return raw if raw else (str(default) if default is not None else "")


def _confirm(label="Confirm?"):
    try:
        return input(f"  {label} [y/N]: ").strip().lower() == "y"
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def _silent_logger():
    log = logging.getLogger("sun2000_tool.lib")
    log.addHandler(logging.NullHandler())
    log.setLevel(logging.CRITICAL)
    return log


# ---------------------------------------------------------------------------
# Connection setup
# ---------------------------------------------------------------------------

def setup_connection():
    _hr("═")
    print("  Huawei SUN2000 Modbus Tool")
    _hr("═")
    print()
    host    = _prompt("Inverter host / IP", "192.168.200.1")
    port    = int(_prompt("Modbus TCP port", 502))
    unit    = int(_prompt("Modbus unit ID", 0))
    version = _prompt("Register version (V1 / V2 / V3)", "V3").upper()

    register_class = inverter_registers.InverterRegister.get(version)

    inverter = inv_module.Sun2000(
        logger=_silent_logger(),
        host=host, port=port,
        modbus_unit=unit,
        timeout=10,
    )

    print(f"\n  Connecting to {host}:{port} (unit {unit}, {version})…", end="", flush=True)
    if not inverter.connect():
        print(" FAILED\n")
        print("  Could not establish a Modbus TCP connection.")
        print("  Check host, port, unit ID and network reachability.")
        sys.exit(1)
    print(" OK\n")
    return inverter, register_class


# ---------------------------------------------------------------------------
# Command 1 — read all registers
# ---------------------------------------------------------------------------

def _format_value(raw, reg_def):
    """Return a human-readable string for a register value."""
    dt = reg_def.data_type

    if reg_def.mapping is not None and not isinstance(raw, str):
        return reg_def.mapping.get(int(raw), f"0x{int(raw):04X}  (unknown)")

    if dt in (datatypes.DataType.BITFIELD16, datatypes.DataType.BITFIELD32):
        if isinstance(raw, str):
            try:
                return f"0x{int(raw, 2):04X}  ({raw})"
            except ValueError:
                return raw
        return f"0x{int(raw):04X}"

    if dt == datatypes.DataType.STRING:
        return str(raw).replace("\x00", "").strip()

    # Numeric (int or float after gain division)
    if isinstance(raw, float) and raw == int(raw):
        return str(int(raw))
    return str(raw)


def cmd_read_all(inverter, register_class):
    _hr()
    print(f"  {'Name':<46} {'Addr':>6}  {'Value':<30} {'Unit':<8}  Access")
    _hr()

    members = sorted(
        register_class.__members__.items(),
        key=lambda item: item[1].value.address,
    )

    ok = err = skipped = 0

    for name, reg in members:
        r = reg.value
        addr = str(r.address)
        access = r.access_type.value.upper()

        if r.access_type == AccessType.WO:
            print(f"  {name:<46} {addr:>6}  {'(write-only)':<30} {'':<8}  {access}")
            skipped += 1
            continue

        if r.data_type == datatypes.DataType.MULTIDATA:
            print(f"  {name:<46} {addr:>6}  {'(multidata — skipped)':<30} {'':<8}  {access}")
            skipped += 1
            continue

        try:
            raw = inverter.read(reg)
            display = _format_value(raw, r)
            unit_str = r.unit or ""
            print(f"  {name:<46} {addr:>6}  {display:<30} {unit_str:<8}  {access}")
            ok += 1
        except Exception as exc:
            short_err = str(exc).split("\n")[0][:32]
            print(f"  {name:<46} {addr:>6}  {'ERR: ' + short_err:<30} {'':<8}  {access}")
            err += 1

    _hr()
    print(f"  {ok} read OK  |  {err} error(s)  |  {skipped} skipped")
    _hr()


# ---------------------------------------------------------------------------
# Command 2 — write power limit
# ---------------------------------------------------------------------------

def cmd_write_power_limit(inverter, register_class):
    _hr()
    print(f"  Write Power Limit  →  register {POWER_LIMIT_REGISTER}"
          "  (ActivePowerPercentageDerating, gain /10, range 0–1000)")
    _hr()

    # Show current value
    try:
        rb = inverter.inverter.read_holding_registers(
            POWER_LIMIT_REGISTER, 1, unit=inverter.modbus_unit)
        cur = rb.registers[0]
        print(f"  Current:  register {POWER_LIMIT_REGISTER} = {cur}  ({cur / 10.0:.1f}%)")
    except Exception:
        print(f"  (Could not read current value of register {POWER_LIMIT_REGISTER})")

    # Determine rated power
    max_power = None
    try:
        if hasattr(register_class, "MaximumActivePower"):
            mp = inverter.read(register_class.MaximumActivePower)
            if mp and float(mp) > 0:
                max_power = float(mp)
                print(f"  MaximumActivePower: {max_power:.0f} W  (read from inverter)")
    except Exception:
        pass

    if not max_power:
        raw = _prompt("Rated power of inverter (W) — needed for W→% conversion", 5000)
        max_power = float(raw)

    print()
    print(f"  Enter the new power limit:")
    print(f"    Watts       e.g.  2500      (0 – {max_power:.0f} W)")
    print(f"    Percentage  e.g.  50%        (0 – 100%)")
    print(f"    none                          remove limit (reset to 100%)")
    print()

    raw = _prompt("New limit")

    if raw.lower() in ("", "none"):
        register_val = 1000
        label = "no limit (100.0%)"
    elif raw.endswith("%"):
        pct = max(0.0, min(100.0, float(raw[:-1].strip())))
        register_val = int(pct * 10)
        label = f"{pct:.1f}%"
    else:
        try:
            watts = float(raw)
        except ValueError:
            print("  Invalid input — enter a number, a percentage, or 'none'.")
            return
        watts = max(0.0, min(max_power, watts))
        pct = (watts / max_power) * 100.0
        register_val = int(pct * 10)
        label = f"{watts:.0f} W  ({pct:.1f}%)"

    print()
    print(f"  Will write  register {POWER_LIMIT_REGISTER} = {register_val}  →  {label}")
    print()

    if not _confirm("Confirm write?"):
        print("  Cancelled.")
        return

    try:
        result = inverter.inverter.write_register(
            POWER_LIMIT_REGISTER, register_val, unit=inverter.modbus_unit)
        if hasattr(result, "isError") and result.isError():
            print(f"  ERROR writing register: {result}")
            return

        # Read back to confirm
        rb = inverter.inverter.read_holding_registers(
            POWER_LIMIT_REGISTER, 1, unit=inverter.modbus_unit)
        rb_val = rb.registers[0]
        status = "✓" if rb_val == register_val else f"✗ unexpected read-back value"
        print(f"  {status}  register {POWER_LIMIT_REGISTER} read-back = {rb_val}  ({rb_val / 10.0:.1f}%)")
    except Exception as exc:
        print(f"  ERROR: {exc}")


# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------

MENU = """\

  1   Read all registers
  2   Write power limit  (register 40125)
  3   Reconnect
  0   Quit
"""


def main():
    inverter, register_class = setup_connection()

    while True:
        _hr()
        print(MENU, end="")
        _hr()
        try:
            choice = input("  Choice: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            cmd_read_all(inverter, register_class)
        elif choice == "2":
            cmd_write_power_limit(inverter, register_class)
        elif choice == "3":
            print("  Reconnecting…", end="", flush=True)
            ok = inverter.connect()
            print(" OK" if ok else " FAILED")
        elif choice == "0":
            break
        else:
            print("  Unknown option.")

    print("\n  Goodbye.\n")


if __name__ == "__main__":
    main()
