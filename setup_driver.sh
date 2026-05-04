#!/bin/bash
echo "=== Huawei SUN2000 Driver Setup ==="
CONTAINER=$(docker ps -q)

echo ">>> pymodbus installeren..."
docker exec $CONTAINER pip3 install pymodbus==2.5.3 -q

echo ">>> Driver kopiëren..."
docker exec $CONTAINER pkill -f dbus-huaweisun2000 2>/dev/null || true
sleep 2
docker cp ~/venus-dev/dbus-huaweisun2000-pvinverter $CONTAINER:/data/dbus-huaweisun2000-pvinverter

echo ">>> D-Bus settings resetten..."
docker exec $CONTAINER dbus-send --system \
  --dest=com.victronenergy.settings \
  --type=method_call \
  /Settings/HuaweiSUN2000/ModbusHost \
  com.victronenergy.BusItem.SetValue \
  variant:string:"host.docker.internal" 2>/dev/null || true
sleep 1
docker exec $CONTAINER dbus-send --system \
  --dest=com.victronenergy.settings \
  --type=method_call \
  /Settings/HuaweiSUN2000/ModbusPort \
  com.victronenergy.BusItem.SetValue \
  variant:int32:5020 2>/dev/null || true
sleep 1
docker exec $CONTAINER dbus-send --system \
  --dest=com.victronenergy.settings \
  --type=method_call \
  /Settings/HuaweiSUN2000/CustomName \
  com.victronenergy.BusItem.SetValue \
  variant:string:"SUN2000-5KTL-L1 Simulator" 2>/dev/null || true
sleep 1
docker exec $CONTAINER dbus-send --system \
  --dest=com.victronenergy.settings \
  --type=method_call \
  /Settings/HuaweiSUN2000/Position \
  com.victronenergy.BusItem.SetValue \
  variant:int32:1 2>/dev/null || true
sleep 1

echo ">>> Driver starten..."
docker exec $CONTAINER bash -c "python3 /data/dbus-huaweisun2000-pvinverter/dbus-huaweisun2000-pvinverter.py > /tmp/driver.log 2>&1 &"

echo ">>> Wachten op driver..."
sleep 12
docker exec $CONTAINER cat /tmp/driver.log | grep -E "Static|status|Error|Settings"

echo ""
echo "=== Validatie ==="
docker exec $CONTAINER dbus-send --system \
  --dest=org.freedesktop.DBus --type=method_call --print-reply \
  /org/freedesktop/DBus org.freedesktop.DBus.ListNames 2>/dev/null | grep pvinverter

echo "Monitor MQTT: mosquitto_sub -h localhost -p 1883 -t 'N/+/pvinverter/#' -v"
