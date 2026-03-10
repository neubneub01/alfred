#!/bin/bash

# IP Info - Alfred 5 Script Filter
# Gathers network information and outputs Alfred JSON items

items=()

# --- Local IP ---
local_ip=$(ipconfig getifaddr en0 2>/dev/null)
if [[ -z "$local_ip" ]]; then
    local_ip=$(ipconfig getifaddr en1 2>/dev/null)
fi
if [[ -z "$local_ip" ]]; then
    local_ip="Unavailable"
fi
items+=("{
    \"title\": \"Local IP: $local_ip\",
    \"subtitle\": \"Press Enter to copy\",
    \"arg\": \"$local_ip\",
    \"icon\": { \"type\": \"fileicon\", \"path\": \"/System/Library/PreferencePanes/Network.prefPane\" }
}")

# --- Public IP ---
public_ip=$(curl -s --max-time 3 ifconfig.me 2>/dev/null)
if [[ -z "$public_ip" ]]; then
    public_ip="Unavailable (timeout or no connection)"
fi
items+=("{
    \"title\": \"Public IP: $public_ip\",
    \"subtitle\": \"Press Enter to copy\",
    \"arg\": \"$public_ip\",
    \"icon\": { \"type\": \"fileicon\", \"path\": \"/System/Library/PreferencePanes/Network.prefPane\" }
}")

# --- Router / Gateway IP ---
gateway_ip=$(netstat -nr 2>/dev/null | grep '^default' | head -1 | awk '{print $2}')
if [[ -z "$gateway_ip" ]]; then
    gateway_ip="Unavailable"
fi
items+=("{
    \"title\": \"Gateway: $gateway_ip\",
    \"subtitle\": \"Press Enter to copy\",
    \"arg\": \"$gateway_ip\",
    \"icon\": { \"type\": \"fileicon\", \"path\": \"/System/Library/PreferencePanes/Network.prefPane\" }
}")

# --- DNS Servers ---
dns_servers=$(scutil --dns 2>/dev/null | grep 'nameserver\[' | awk '{print $3}' | sort -u | head -3 | tr '\n' ', ' | sed 's/,$//')
if [[ -z "$dns_servers" ]]; then
    dns_servers="Unavailable"
fi
items+=("{
    \"title\": \"DNS: $dns_servers\",
    \"subtitle\": \"Press Enter to copy\",
    \"arg\": \"$dns_servers\",
    \"icon\": { \"type\": \"fileicon\", \"path\": \"/System/Library/PreferencePanes/Network.prefPane\" }
}")

# --- Wi-Fi SSID ---
wifi_ssid=$(networksetup -getairportnetwork en0 2>/dev/null | sed 's/^Current Wi-Fi Network: //')
if [[ -z "$wifi_ssid" || "$wifi_ssid" == *"not associated"* || "$wifi_ssid" == *"not find"* ]]; then
    wifi_ssid="Not connected"
fi
items+=("{
    \"title\": \"Wi-Fi: $wifi_ssid\",
    \"subtitle\": \"Press Enter to copy\",
    \"arg\": \"$wifi_ssid\",
    \"icon\": { \"type\": \"fileicon\", \"path\": \"/System/Library/PreferencePanes/Network.prefPane\" }
}")

# --- Build JSON output ---
json="{\"items\": ["
for i in "${!items[@]}"; do
    if [[ $i -gt 0 ]]; then
        json+=","
    fi
    json+="${items[$i]}"
done
json+="]}"

echo "$json"
