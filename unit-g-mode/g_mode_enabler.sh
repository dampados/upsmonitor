#!/bin/bash
# Enable WoL g-mode on all physical interfaces that support it

for iface in $(ls /sys/class/net/ | grep -v lo); do
    [ -d "/sys/class/net/$iface/device" ] || continue
    ethtool "$iface" 2>/dev/null | grep -q "Supports Wake-on:.*g" || continue
    ethtool -s "$iface" wol g 2>/dev/null && echo "Enabled WoL on $iface"
done