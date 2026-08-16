---
title: Nmap Cheatsheet
slug: nmap
date: 2026-07-20
updated: 2026-08-10
tags: [Nmap, Enumeration, Scanning, Recon, Networking]
description: The Nmap flags and scan recipes I reach for on every engagement — from the first sweep to targeted script scans.
---

The commands here are ordered the way I actually run them: **fast and wide
first, slow and deep second.**

## The two-step opener

```bash
# 1. Find every open TCP port, fast, no frills
nmap -p- --min-rate 2000 -T4 -oN nmap/all-ports.txt <TARGET>

# 2. Deep-scan only the ports that were open
nmap -sC -sV -p 22,80,445 -oN nmap/services.txt <TARGET>
```

Doing it in two passes is dramatically faster than `-sC -sV -p-` on everything.

## Host discovery

```bash
nmap -sn 10.10.10.0/24              # ping sweep, no port scan
nmap -Pn <TARGET>                   # skip discovery, treat host as up
```

## Scan types

| Flag  | Meaning                            | Notes                          |
|-------|------------------------------------|--------------------------------|
| `-sS` | SYN "stealth" scan (default root)  | Fast, half-open                |
| `-sT` | Full TCP connect                   | Used when not root             |
| `-sU` | UDP scan                           | Slow — scope it to key ports   |
| `-sV` | Service/version detection          | Maps versions to CVEs          |
| `-O`  | OS detection                       | Needs root                     |
| `-sC` | Default NSE scripts                | Same as `--script=default`     |

## Timing and performance

```bash
-T4                 # aggressive timing (safe on most labs)
--min-rate 2000     # send at least N packets/sec
--max-retries 2     # stop wasting time on filtered ports
```

!!! tip "Save everything"
    Always write output with `-oA nmap/scan` (or `-oN`). You will want to grep
    old scans later, and re-scanning wastes time and makes noise.

## UDP — the top ports only

```bash
# UDP is slow; scan the usual suspects rather than all 65535
nmap -sU --top-ports 20 -oN nmap/udp.txt <TARGET>
```

## Useful NSE scripts

```bash
# Enumerate SMB shares and users
nmap --script "smb-enum-shares,smb-enum-users" -p 445 <TARGET>

# Grab HTTP titles and enumerate directories
nmap --script "http-title,http-enum" -p 80,443 <TARGET>

# Check for known vulns (broad, noisy)
nmap --script vuln -p <PORT> <TARGET>
```

## Output formats

```bash
-oN file.txt     # normal, human-readable
-oG file.gm      # greppable
-oX file.xml     # XML (feed into other tools)
-oA nmap/scan    # all three at once
```

## One-liner I keep in my notes

```bash
# Full opener in a single line: all ports, then auto-deep-scan the open ones
ports=$(nmap -p- --min-rate 2000 -T4 <TARGET> | grep '^[0-9]' | cut -d/ -f1 | paste -sd,) \
  && nmap -sC -sV -p"$ports" -oN nmap/deep.txt <TARGET>
```
