#!/bin/bash
# Interactive configuration script for Huawei SUN2000 driver
# Usage: ./configure.sh

set -e

echo "=========================================="
echo "Huawei SUN2000 Driver Configuration"
echo "=========================================="
echo ""

# Check if running on Venus OS
if ! command -v dbus &> /dev/null; then
    echo "ERROR: This script must be run on Venus OS"
    exit 1
fi

# Get current settings
get_current_value() {
    local path=$1
    dbus -y com.victronenergy.settings "$path" GetValue 2>/dev/null || echo "not set"
}

echo "Current settings:"
echo "----------------"
CURRENT_HOST=$(get_current_value "/Settings/HuaweiSUN2000/ModbusHost")
CURRENT_PORT=$(get_current_value "/Settings/HuaweiSUN2000/ModbusPort")
CURRENT_UNIT=$(get_current_value "/Settings/HuaweiSUN2000/ModbusUnit")
CURRENT_VERSION=$(get_current_value "/Settings/HuaweiSUN2000/ModbusVersion")
CURRENT_SYSTEM=$(get_current_value "/Settings/HuaweiSUN2000/SystemType")
CURRENT_PHASE=$(get_current_value "/Settings/HuaweiSUN2000/SinglePhasePosition")

echo "  Modbus Host: $CURRENT_HOST"
echo "  Modbus Port: $CURRENT_PORT"
echo "  Modbus Unit: $CURRENT_UNIT"
echo "  Register Version: $CURRENT_VERSION"
echo "  System Type: $CURRENT_SYSTEM (0=Single-phase, 1=Three-phase)"
echo "  Single-phase Position: $CURRENT_PHASE (1=L1, 2=L2, 3=L3)"
echo ""

read -p "Do you want to change the configuration? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Configuration unchanged."
    exit 0
fi

echo ""
echo "=========================================="
echo "Configure Modbus Connection"
echo "=========================================="

# Modbus Host
echo ""
echo "Enter the IP address of your Huawei inverter"
echo "  - For real inverter: e.g., 192.168.1.100"
echo "  - For simulator on same network: your simulator IP"
read -p "Modbus Host [$CURRENT_HOST]: " NEW_HOST
NEW_HOST=${NEW_HOST:-$CURRENT_HOST}

# Modbus Port
echo ""
echo "Enter the Modbus TCP port"
echo "  - 6607: SDongle WLAN-FE (most common)"
echo "  - 502: Direct Ethernet connection"
echo "  - 5020: For simulator"
read -p "Modbus Port [$CURRENT_PORT]: " NEW_PORT
NEW_PORT=${NEW_PORT:-$CURRENT_PORT}

# Modbus Unit
echo ""
echo "Enter the Modbus Unit ID"
echo "  - Usually 0 (try 1 if 0 doesn't work)"
read -p "Modbus Unit [$CURRENT_UNIT]: " NEW_UNIT
NEW_UNIT=${NEW_UNIT:-$CURRENT_UNIT}

# Modbus Version
echo ""
echo "Select Register Map Version:"
echo "  V3: Most models post-2019 (SUN2000-xKTL-L1/M1/M2/M3)"
echo "  V2: Older models via SmartLogger"
read -p "Register Version (V2/V3) [$CURRENT_VERSION]: " NEW_VERSION
NEW_VERSION=${NEW_VERSION:-$CURRENT_VERSION}
NEW_VERSION=$(echo "$NEW_VERSION" | tr '[:lower:]' '[:upper:]')

# System Type
echo ""
echo "Select System Type:"
echo "  0: Single-phase inverter"
echo "  1: Three-phase inverter"
read -p "System Type (0/1) [$CURRENT_SYSTEM]: " NEW_SYSTEM
NEW_SYSTEM=${NEW_SYSTEM:-$CURRENT_SYSTEM}

# Single-phase Position (only if single-phase)
if [ "$NEW_SYSTEM" -eq 0 ]; then
    echo ""
    echo "Select which phase to report single-phase data on:"
    echo "  1: L1"
    echo "  2: L2"
    echo "  3: L3"
    echo "  (Choose the phase your inverter is physically connected to)"
    read -p "Single-phase Position (1/2/3) [$CURRENT_PHASE]: " NEW_PHASE
    NEW_PHASE=${NEW_PHASE:-$CURRENT_PHASE}
else
    NEW_PHASE=$CURRENT_PHASE
fi

# Summary
echo ""
echo "=========================================="
echo "Configuration Summary"
echo "=========================================="
echo "  Modbus Host: $NEW_HOST"
echo "  Modbus Port: $NEW_PORT"
echo "  Modbus Unit: $NEW_UNIT"
echo "  Register Version: $NEW_VERSION"
echo "  System Type: $NEW_SYSTEM"
if [ "$NEW_SYSTEM" -eq 0 ]; then
    echo "  Single-phase Position: L$NEW_PHASE"
fi
echo ""

read -p "Apply this configuration? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Configuration cancelled."
    exit 0
fi

# Apply settings via D-Bus
echo ""
echo "Applying configuration..."

dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/ModbusHost SetValue "$NEW_HOST"
dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/ModbusPort SetValue $NEW_PORT
dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/ModbusUnit SetValue $NEW_UNIT
dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/ModbusVersion SetValue "$NEW_VERSION"
dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/SystemType SetValue $NEW_SYSTEM
dbus -y com.victronenergy.settings /Settings/HuaweiSUN2000/SinglePhasePosition SetValue $NEW_PHASE

echo "✓ Configuration applied successfully"

# Restart driver
echo ""
read -p "Restart driver to apply changes? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Restarting driver..."
    /data/dbus-huaweisun2000-pvinverter/restart.sh
    echo "✓ Driver restarted"
    echo ""
    echo "Check driver logs with:"
    echo "  tail -f /var/log/dbus-huaweisun2000/current | tai64nlocal"
else
    echo ""
    echo "Configuration saved but driver not restarted."
    echo "Run this to apply changes:"
    echo "  /data/dbus-huaweisun2000-pvinverter/restart.sh"
fi

echo ""
echo "=========================================="
echo "Configuration complete!"
echo "=========================================="
echo ""
echo "To reconfigure later, run:"
echo "  /data/dbus-huaweisun2000-pvinverter/configure.sh"
echo ""
