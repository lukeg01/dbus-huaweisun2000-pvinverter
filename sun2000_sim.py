#!/usr/bin/env python3
"""
Huawei SUN2000-5KTL-L1 Modbus TCP Simulator
Registeradressen exact gebaseerd op InverterRegisterV3
pymodbus 2.5.3 - alle adressen 1-based, intern omgezet naar 0-based via [addr-1]
"""

import logging
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
log = logging.getLogger("sun2000-sim")

hr = [0] * 50000

def reg(addr, value):
    """Stel een register in. addr is Huawei 1-based, intern 0-based = addr-1."""
    hr[addr] = value

def reg32(addr, value):
    """Stel een 32-bit register in. addr is Huawei 1-based."""
    hr[addr] = (value >> 16) & 0xFFFF
    hr[addr + 1] = value & 0xFFFF

def str_reg(s, addr, count):
    """Schrijf string. addr is Huawei 1-based."""
    s = s.ljust(count * 2)
    for i in range(count):
        hr[addr + i] = (ord(s[i*2]) << 8) | ord(s[i*2+1])

# ── Statische identificatie ───────────────────────────────────────────────
str_reg("SUN2000-5KTL-L1",  30000, 15)   # Model
str_reg("HV2340123456",     30015, 10)   # SN
str_reg("02354KAA",         30025, 10)   # PN
reg(30070, 344)                           # ModelID
reg(30071, 2)                             # NumberOfPVStrings
reg(30072, 1)                             # NumberOfMPPTrackers
reg32(30073, 5000)                        # RatedPower: 5000W
reg32(30075, 5000)                        # MaximumActivePower: 5000W

# ── PV strings ───────────────────────────────────────────────────────────
reg(32016, 3750)   # PV1 voltage: 375.0V  (gain /10)
reg(32017, 800)    # PV1 current: 8.00A   (gain /100)
reg(32018, 3700)   # PV2 voltage: 370.0V
reg(32019, 750)    # PV2 current: 7.50A

# ── DC input power ────────────────────────────────────────────────────────
reg32(32064, 5850) # InputPower: 5850W    (gain /1 W)

# ── Grid meetwaarden ─────────────────────────────────────────────────────
reg(32066, 2300)   # LineVoltage AB: 230.0V (gain /10)
reg(32069, 2300)   # PhaseA voltage: 230.0V (gain /10)
reg(32070, 0)      # PhaseB: n.v.t.
reg(32071, 0)      # PhaseC: n.v.t.
reg32(32072, 21300) # PhaseA current: 21.300A (gain /1000)
reg32(32074, 0)    # PhaseB current
reg32(32076, 0)    # PhaseC current
reg32(32078, 5000) # PeakActivePower: 5000W (gain /1 W)
reg32(32080, 4900) # ActivePower: 4900W     (gain /1 W)
reg32(32082, 150)  # ReactivePower: 0.150kvar
reg(32084, 999)    # PowerFactor: 0.999     (gain /1000)
reg(32085, 5000)   # GridFrequency: 50.00Hz (gain /100)
reg(32086, 9760)   # Efficiency: 97.60%     (gain /100)
reg(32087, 420)    # InternalTemperature: 42.0°C (gain /10)
reg(32088, 1500)   # InsulationResistance: 1.500MOhm
reg(32089, 0x0200) # DeviceStatus: On-grid
reg(32090, 0)      # FaultCode: geen

# ── Energie ───────────────────────────────────────────────────────────────
reg32(32106, 1234567) # AccumulatedEnergyYield: 12345.67kWh (gain /100)
reg32(32114, 2345)    # DailyEnergyYield: 23.45kWh

# ── Power scheduling ──────────────────────────────────────────────────────
reg(40125, 1000)   # ActivePowerPercentageDerating: 100.0% (gain /10)
reg(40200, 0)      # PowerOn command
reg(40201, 0)      # Shutdown command


class SUN2000Slave(ModbusSlaveContext):
    def setValues(self, fc, address, values):
        super().setValues(fc, address, values)
        if fc in (6, 16):
            addr_1based = address + 1
            if addr_1based == 40200 and values[0] == 1:
                log.info(">>> POWER ON — status → On-grid (0x0200)")
                super().setValues(3, 32089 - 1, [0x0200])
                super().setValues(3, 32080 - 1, [0])
                super().setValues(3, 32081 - 1, [4900])
            elif addr_1based == 40201 and values[0] == 1:
                log.info(">>> SHUTDOWN — status → Standby (0x0300)")
                super().setValues(3, 32089 - 1, [0x0300])
                super().setValues(3, 32080 - 1, [0])
                super().setValues(3, 32081 - 1, [0])
            elif address == 40125:
                pct = values[0] / 10.0
                log.info(f">>> POWER LIMIT: {pct:.1f}%")
                limited = int(4900 * pct / 100)
                super().setValues(3, 32081, [limited])
                if values[0] == 0:
                    super().setValues(3, 32089, [0x0304])  # Shutdown: power limited
                elif values[0] < 1000:
                    super().setValues(3, 32089, [0x0201])  # Grid connection: power limited
                else:
                    super().setValues(3, 32089, [0x0200])  # On-grid


store = SUN2000Slave(hr=ModbusSequentialDataBlock(1, hr))
context = ModbusServerContext(slaves=store, single=True)

log.info("Huawei SUN2000-5KTL-L1 simulator gestart op 0.0.0.0:5020")
log.info("V3 registermap | 4900W | 230V | 50Hz | 42C")

StartTcpServer(context, address=("0.0.0.0", 5020))
