---
title: "Network Segmentation for Homelabs"
date: 2026-08-02
description: "A practical guide to segmenting your homelab network with VLANs, firewall rules, and IoT isolation — no enterprise buzzwords, just working configs."
tags: ["homelab", "networking", "vlan", "firewall", "iot-security"]
categories: ["articles"]
author: "Arman Abrahamyan"
---

# Network Segmentation for Homelabs

> Your smart fridge shouldn't be able to scan your NAS. Network segmentation isn't just for enterprises — it's the single most impactful security upgrade you can make to a homelab. This guide covers practical VLAN setup, firewall rules, and IoT isolation using common consumer and prosumer gear.

---

## Why Segment Your Network?

Without segmentation, every device on your network can talk to every other device. This means:

- A compromised smart bulb can probe your file server
- A guest's malware-infected laptop can reach your Home Assistant instance
- IoT devices with weak credentials become pivot points for lateral movement

**Segmentation limits the blast radius.** If one zone is compromised, the attacker still needs to cross a firewall to reach other zones.

---

## Network Zones


| VLAN | Name | Purpose | Trust Level |
|------|------|---------|-------------|
| 10 | TRUST | Personal devices, servers, NAS | High |
| 20 | IOT | Smart home devices, cameras | Low |
| 30 | GUEST | Visitor devices, untrusted | Untrusted |
| 40 | MGMT | Management interfaces (optional) | High |
| 50 | CAM | Security cameras only (optional) | Low |

---

## Hardware Options

You don't need a $500 enterprise switch. Here are practical options:

| Budget | Router/Firewall | Switch | Notes |
|--------|----------------|--------|-------|
| $0 (reuse) | Old PC + pfSense | Managed switch (eBay) | Best performance |
| $150 | UniFi Dream Router | Built-in | All-in-one, cloud-managed |
| $200 | Protectli Vault | UniFi Switch Lite | Fanless, low power |
| $300+ | OPNsense on mini-PC | Cisco SG350 | Full enterprise features |

**Minimum requirement:** A router/firewall that supports VLANs and a managed switch (or Wi-Fi access points with VLAN tagging).

---

## VLAN Configuration

### pfSense / OPNsense

**1. Create VLANs:**

Navigate to **Interfaces → Assignments → VLANs** and create:

| VLAN Tag | Description | Parent Interface |
|----------|-------------|------------------|
| 10 | TRUST | LAN (em0) |
| 20 | IOT | LAN (em0) |
| 30 | GUEST | LAN (em0) |

**2. Assign Interfaces:**

Go to **Interfaces → Assignments** and assign each VLAN to a new interface:

- `OPT1` → VLAN 10 (TRUST)
- `OPT2` → VLAN 20 (IOT)
- `OPT3` → VLAN 30 (GUEST)

**3. Enable DHCP for Each VLAN:**

```
Services → DHCP Server → TRUST
  Range: 192.168.10.100 - 192.168.10.200

Services → DHCP Server → IOT
  Range: 192.168.20.100 - 192.168.20.200

Services → DHCP Server → GUEST
  Range: 192.168.30.100 - 192.168.30.200
```

---

## Firewall Rules

This is where the security happens. The default stance should be **deny all, allow explicitly**.

### Zone Trust Model

```
TRUST  → can reach → IOT, GUEST, INTERNET
IOT    → can reach → INTERNET only (blocked from TRUST)
GUEST  → can reach → INTERNET only (blocked from TRUST, IOT)
```

### pfSense Rules

**TRUST (VLAN 10) — Allow outbound:**

```
Action: Pass
Interface: TRUST
Protocol: Any
Source: TRUST net
Destination: Any
Description: Allow all outbound from TRUST
```

**IOT (VLAN 20) — Block TRUST, allow Internet:**

```
Action: Block
Interface: IOT
Protocol: Any
Source: IOT net
Destination: TRUST net
Description: Block IOT from reaching TRUST

Action: Pass
Interface: IOT
Protocol: Any
Source: IOT net
Destination: Any
Description: Allow IOT to Internet
```

**GUEST (VLAN 30) — Isolate completely:**

```
Action: Block
Interface: GUEST
Protocol: Any
Source: GUEST net
Destination: RFC1918 networks (10/8, 172.16/12, 192.168/16)
Description: Block GUEST from all private networks

Action: Pass
Interface: GUEST
Protocol: TCP/UDP
Source: GUEST net
Destination: Any
Port: 53, 443, 80
Description: Allow DNS and web only
```

### OPNsense (Same Logic, Different UI)

```
Firewall → Rules → IOT
  Add rule:
    Action: Block
    Direction: in
    TCP/IP Version: IPv4
    Protocol: any
    Source: IOT net
    Destination: TRUST net

  Add rule:
    Action: Pass
    Direction: in
    TCP/IP Version: IPv4  
    Protocol: any
    Source: IOT net
    Destination: any
```

---

## Switch Configuration

### UniFi Switch (via Controller)

**1. Create Networks:**

```
Settings → Networks → Create New
  Name: TRUST
  VLAN ID: 10
  Gateway: 192.168.10.1/24

Settings → Networks → Create New
  Name: IOT
  VLAN ID: 20
  Gateway: 192.168.20.1/24

Settings → Networks → Create New
  Name: GUEST
  VLAN ID: 30
  Gateway: 192.168.30.1/24
```

**2. Configure Switch Ports:**

```
Devices → Switch → Ports

Port 1 (Router uplink):
  Profile: ALL (trunk — carries all VLANs)

Port 2 (NAS/Server):
  Profile: TRUST

Port 3 (Smart Hub):
  Profile: IOT

Port 4 (Access Point):
  Profile: ALL (AP needs trunk for multiple SSIDs)
```

### Cisco SG350 (CLI)

```cisco
enable
configure terminal

! Create VLANs
vlan 10
 name TRUST
vlan 20
 name IOT
vlan 30
 name GUEST
exit

! Configure trunk port to router
interface gigabitethernet1
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30
exit

! Configure access ports
interface gigabitethernet2
 switchport mode access
 switchport access vlan 10
 description NAS-SERVER
exit

interface gigabitethernet3
 switchport mode access
 switchport access vlan 20
 description SMART-HUB
exit
```

---

## Wi-Fi Segmentation

Your access point should broadcast separate SSIDs for each zone:

| SSID | VLAN | Password | Purpose |
|------|------|----------|---------|
| `Home-Net` | 10 | Strong | Personal devices |
| `Home-IOT` | 20 | Medium | Smart devices (can be hidden) |
| `Home-Guest` | 30 | Easy/QR | Visitors |

### UniFi AP Configuration

```
Settings → WiFi → Add New Network
  Name: Home-IOT
  Security: WPA2/WPA3
  Password: [generate strong]
  Network: IOT (VLAN 20)
  Advanced:
    Hide SSID: Yes
    Band: 2.4GHz only (most IoT doesn't support 5GHz)
    Client Isolation: Yes
```

---

## IoT Device Hardening Checklist

Segmentation is layer 1. Add these for defense in depth:

- **Change default passwords** on every IoT device
- **Disable UPnP** on the router (IoT devices shouldn't open ports)
- **Disable unused services** (telnet, SSH, web admin if not needed)
- **Firmware updates** — enable auto-update where available
- **No IoT cloud access** if local control works (Home Assistant, Zigbee2MQTT)
- **Camera isolation** — separate VLAN with no Internet access, NVR only
- **DNS filtering** — Pi-hole/AdGuard on IOT VLAN to block C2 domains

---

## Testing Your Segmentation

Verify your rules actually work:

```bash
# From TRUST zone (192.168.10.x)
ping 192.168.20.1        # Should work (router)
ping 192.168.20.100      # Should work (IoT device)
nmap 192.168.20.0/24     # Should see IoT devices

# From IOT zone (192.168.20.x)
ping 192.168.10.1        # Should work (router)
ping 192.168.10.100      # Should FAIL (blocked by firewall)
curl http://192.168.10.10 # Should FAIL

# From GUEST zone (192.168.30.x)
ping 192.168.10.100      # Should FAIL
ping 192.168.20.100      # Should FAIL
curl https://google.com  # Should work
```

Use `tcpdump` on your router to verify traffic is being dropped:

```bash
# pfSense/OPNsense shell
tcpdump -i em0.20 -n host 192.168.10.100
# Watch for blocked packets from IOT to TRUST
```

---

## Advanced: Inter-VLAN Services

Sometimes devices in different zones *do* need to talk. Examples:

- Home Assistant (TRUST) → Zigbee hub (IOT)
- Phone (TRUST) → Security camera (IOT)
- NVR (TRUST) → IP cameras (CAM)

**The Rule:** Allow only specific ports, not entire zones.

### Example: Home Assistant → Zigbee Hub

```
pfSense Rule:
  Action: Pass
  Interface: TRUST
  Protocol: TCP/UDP
  Source: Home Assistant IP (192.168.10.50)
  Destination: Zigbee Hub IP (192.168.20.10)
  Port: 8080 (Zigbee2MQTT web UI) or 1883 (MQTT)
  Description: HA to Zigbee Hub
```

### Example: Phone App → Camera

```
pfSense Rule:
  Action: Pass
  Interface: TRUST
  Protocol: TCP
  Source: TRUST net
  Destination: Camera subnet (192.168.50.0/24)
  Port: 554 (RTSP), 80 (HTTP)
  Description: Allow RTSP from TRUST to cameras
```

---

## Monitoring & Alerting

Set up alerts for suspicious cross-VLAN traffic:

```bash
# OPNsense: Log blocked IOT → TRUST attempts
# System → Settings → Logging → Targets
# Add remote syslog to your SIEM or Graylog
```

**What to alert on:**
- Repeated blocked connections from IOT to TRUST
- New MAC addresses on TRUST VLAN
- Port scans detected by Suricata (IDS/IPS)
- DHCP requests from unknown devices

---

## Conclusion

Network segmentation transforms your flat, vulnerable home network into a layered defense architecture. The investment is minimal — an old PC or a $150 router — but the security return is enormous.

**Start simple:** Three VLANs (TRUST, IOT, GUEST) with basic firewall rules. **Then iterate:** Add camera isolation, DNS filtering, and IDS/IPS as you grow.

> **Remember:** The goal isn't perfection. The goal is making an attacker's job significantly harder than it's worth.

---

## Resources

- [pfSense Documentation](https://docs.netgate.com/pfsense/en/latest/)
- [OPNsense Documentation](https://docs.opnsense.org/)
- [UniFi Network Design](https://help.ui.com/hc/en-us/articles/360012282453)
- [Practical Networking — VLANs Explained](https://www.practicalnetworking.net/stand-alone/vlans/)
- [OWASP IoT Security Guidance](https://owasp.org/www-project-internet-of-things/)
