#!/bin/bash
echo "=== Huawei SUN2000 Driver Validatie ==="
CONTAINER=$(docker ps -q)
PORTAL_ID=$(mosquitto_sub -h localhost -p 1883 -t "N/#" -v -C 1 2>/dev/null | grep -o 'N/[^/]*' | head -1 | cut -d'/' -f2)

echo ""
echo "--- 1. Driver process ---"
docker exec $CONTAINER ps aux | grep dbus-huawei | grep -v grep && echo "OK: driver draait" || echo "FOUT: driver niet actief"

echo ""
echo "--- 2. Driver logs ---"
docker exec $CONTAINER cat /tmp/driver.log | grep -E "Static|status changed|Error|Settings: Modbus"

echo ""
echo "--- 3. D-Bus registratie ---"
DBUS=$(docker exec $CONTAINER dbus-send --system \
  --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames 2>/dev/null | grep pvinverter)
if [ -n "$DBUS" ]; then
    echo "OK: $DBUS"
else
    echo "FOUT: pvinverter niet geregistreerd op D-Bus"
fi

echo ""
echo "--- 4. Modbus verbinding vanuit container ---"
docker exec $CONTAINER python3 -c "
from pymodbus.client.sync import ModbusTcpClient
c = ModbusTcpClient('host.docker.internal', port=5020, timeout=3)
if c.connect():
    r = c.read_holding_registers(32080, 2, unit=0)
    print('OK: ActivePower =', r.registers[1], 'W') if hasattr(r, 'registers') else print('FOUT: registers')
    r2 = c.read_holding_registers(32069, 1, unit=0)
    print('OK: PhaseAVoltage =', r2.registers[0]/10, 'V') if hasattr(r2, 'registers') else print('FOUT: voltage')
    r3 = c.read_holding_registers(32089, 1, unit=0)
    print('OK: DeviceStatus =', hex(r3.registers[0])) if hasattr(r3, 'registers') else print('FOUT: status')
else:
    print('FOUT: geen verbinding met simulator')
c.close()
" 

echo ""
echo "--- 5. MQTT meetwaarden ---"
echo "Wachten op MQTT data (5 seconden)..."
mosquitto_pub -h localhost -p 1883 \
  -t "R/$PORTAL_ID/pvinverter/1/Ac/Power" -m "" 2>/dev/null
VALUES=$(mosquitto_sub -h localhost -p 1883 \
  -t "N/$PORTAL_ID/pvinverter/#" -v -C 30 -W 5 2>/dev/null | \
  grep -v UpdateIndex)
if [ -n "$VALUES" ]; then
    echo "OK: meetwaarden ontvangen:"
    echo "$VALUES" | head -10
else
    echo "INFO: alleen UpdateIndex ontvangen"
fi

echo ""
echo "--- 6. Simulator status ---"
python3 << 'PYEOF'
from pymodbus.client.sync import ModbusTcpClient
c = ModbusTcpClient('127.0.0.1', port=5020, timeout=3)
if c.connect():
    r = c.read_holding_registers(32089, 1, unit=0)
    status = hex(r.registers[0]) if hasattr(r, 'registers') else 'onbekend'
    r2 = c.read_holding_registers(32080, 2, unit=0)
    power = r2.registers[1] if hasattr(r2, 'registers') else 0
    status_str = 'On-grid' if status == '0x200' else 'Standby'
    print(f"OK: DeviceStatus={status} ({status_str}), ActivePower={power}W")
else:
    print("FOUT: simulator niet bereikbaar op poort 5020")
c.close()
PYEOF

echo ""
echo "=== Validatie compleet ==="
