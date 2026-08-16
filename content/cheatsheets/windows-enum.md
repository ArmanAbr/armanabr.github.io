---
layout: page
title: "Windows Enumeration Cheatsheet"
description:  "A comprehensive guide for enumerating Windows systems during CTFs and penetration testing."
icon: "windows"
permalink: /cheatsheets/windows-enum/
---

# Windows Enumeration Cheatsheet

---

## 📋 Table of Contents
1. [System Information](#system-information)
2. [Users & Groups](#users--groups)
3. [Network](#network)
4. [Processes & Services](#processes--services)
5. [Files & Permissions](#files--permissions)
6. [Registry](#registry)
7. [Scheduled Tasks](#scheduled-tasks)
8. [Installed Software](#installed-software)
9. [Privilege Escalation](#privilege-escalation)
10. [Interesting Files & Locations](#interesting-files--locations)
11. [PowerShell Enumeration](#powershell-enumeration)
12. [WMI Queries](#wmi-queries)

---

## System Information

### CMD
```cmd
systeminfo                  # Detailed system information
systeminfo | findstr /B /C:"OS" /C:"System" /C:"Hotfix"
ver                         # Windows version
hostname                    # Computer name
echo %username%             # Current user
echo %userdomain%           # Domain name
echo %logonserver%          # Logon server
wmic computersystem get name, domain, manufacturer, model, username
wmic os get caption, version, osarchitecture, installdate
wmic qfe get caption, description, hotfixid, installedon  # Installed patches
```

### PowerShell
```powershell
Get-ComputerInfo
Get-WmiObject -Class Win32_OperatingSystem | Select-Object *
Get-HotFix
[System.Environment]::OSVersion.Version
```

---

## Users & Groups

### CMD
```cmd
whoami                      # Current user
whoami /priv                # Current user privileges
whoami /groups              # Current user groups
whoami /all                 # All user info

net user                    # List all local users
net user <username>         # Info about specific user
net localgroup              # List all local groups
net localgroup <groupname>  # Members of specific group
net localgroup administrators
net accounts                # Password policy

# Domain users (if domain joined)
net user /domain
net group /domain
net group "Domain Admins" /domain
```

### PowerShell
```powershell
Get-LocalUser
Get-LocalUser | Select-Object Name, Enabled, LastLogonDate
Get-LocalGroup
Get-LocalGroupMember -Group "Administrators"
Get-LocalGroupMember -Group "Remote Desktop Users"

# Domain
Get-ADUser -Filter * | Select-Object Name, SamAccountName
Get-ADGroup -Filter * | Select-Object Name
Get-ADGroupMember -Identity "Domain Admins"
```

---

## Network

### CMD
```cmd
ipconfig                    # IP configuration
ipconfig /all               # Detailed IP config
ipconfig /displaydns        # DNS cache

route print                 # Routing table
arp -a                      # ARP table
netstat -ano                # Active connections with PIDs
netstat -anob               # With process names (requires admin)

# Firewall
netsh advfirewall show allprofiles
netsh advfirewall firewall show rule name=all
netsh firewall show state

# Network shares
net share                   # Local shares
net use                     # Connected shares
net view                    # Visible shares
net view \\<computer>       # Shares on remote computer
```

### PowerShell
```powershell
Get-NetIPConfiguration
Get-NetIPAddress
Get-NetRoute
Get-NetTCPConnection
Get-NetUDPEndpoint
Get-DnsClientCache
Get-NetFirewallRule | Where-Object {$_.Enabled -eq 'True'}
Get-SmbShare
Get-SmbConnection
```

---

## Processes & Services

### CMD
```cmd
tasklist                    # Running processes
tasklist /svc               # Processes with services
tasklist /v                 # Verbose process info
tasklist /fi "STATUS eq RUNNING"
tasklist | findstr <process_name>

# Services
sc query                    # All services
sc query type= service state= all
sc query <servicename>      # Specific service info
net start                   # Running services
wmic service list brief
wmic service get name,displayname,pathname,startmode
```

### PowerShell
```powershell
Get-Process
Get-Process | Select-Object Name, Id, Path, Company
Get-Process | Where-Object {$_.Path -like "*temp*" -or $_.Path -like "*appdata*"}

Get-Service
Get-Service | Where-Object {$_.Status -eq 'Running'}
Get-WmiObject -Class Win32_Service | Select-Object Name, State, PathName, StartName
Get-WmiObject -Class Win32_Service | Where-Object {$_.StartName -notlike "LocalSystem" -and $_.StartName -notlike "NT AUTHORITY*"}
```

---

## Files & Permissions

### CMD
```cmd
dir /s /b <file>            # Search for file recursively
dir /s /b *.txt
dir /s /b *.config
dir /s /b *.xml

# Check permissions
icacls <file>               # File permissions
icacls C:\                 # Directory permissions
accesschk.exe -uws "Everyone" "C:\Program Files"  # Requires Sysinternals
accesschk.exe -uwcqv "Authenticated Users" *      # Service permissions
```

### PowerShell
```powershell
Get-ChildItem -Path C:\ -Recurse -ErrorAction SilentlyContinue | Where-Object {!$_.PSIsContainer}
Get-ChildItem -Path C:\ -Include *.txt,*.config,*.xml,*.ini -Recurse -ErrorAction SilentlyContinue

# Check permissions
Get-Acl C:\Windows
Get-Acl C:\Windows | Format-List
(Get-Acl C:\).Access | Where-Object {$_.IdentityReference -like "*Users*"}

# Find unquoted service paths
Get-WmiObject -Class Win32_Service | Where-Object {$_.PathName -notlike '"*"' -and $_.PathName -like '* *'}

# Find writable directories in PATH
$env:Path -split ';' | ForEach-Object { Get-Acl $_ | Where-Object { $_.AccessToString -match 'Write' } }
```

---

## Registry

### CMD
```cmd
reg query HKLM\Software\Microsoft\Windows\CurrentVersion\Run
reg query HKCU\Software\Microsoft\Windows\CurrentVersion\Run
reg query HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce
reg query HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce

# Auto-login credentials
reg query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"

# Stored passwords
reg query HKLM /f password /t REG_SZ /s
reg query HKCU /f password /t REG_SZ /s

# VNC passwords
reg query "HKCU\Software\ORL\WinVNC3\Password"
reg query "HKCU\Software\TightVNC\Server"

# Putty sessions
reg query "HKCU\Software\SimonTatham\PuTTY\Sessions"

# SNMP community strings
reg query "HKLM\SYSTEM\CurrentControlSet\Services\SNMP\Parameters\ValidCommunities"
```

### PowerShell
```powershell
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Run
Get-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\Run
Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" | Select-Object AutoAdminLogon, DefaultUserName, DefaultPassword
```

---

## Scheduled Tasks

### CMD
```cmd
schtasks /query /fo LIST /v
schtasks /query /fo TABLE
schtasks /query /tn <taskname> /v
```

### PowerShell
```powershell
Get-ScheduledTask
Get-ScheduledTask | Where-Object {$_.State -eq 'Running'}
Get-ScheduledTask | Get-ScheduledTaskInfo
Get-ScheduledTask | Where-Object {$_.TaskPath -eq '\'} | Select-Object TaskName, TaskPath, Author
```

---

## Installed Software

### CMD
```cmd
wmic product get name,version,vendor
wmic product get name,version | findstr /i <keyword>

# 32-bit software
reg query HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall /s
reg query HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall /s
```

### PowerShell
```powershell
Get-WmiObject -Class Win32_Product | Select-Object Name, Version, Vendor
Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Select-Object DisplayName, DisplayVersion, Publisher
Get-ItemProperty HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Select-Object DisplayName, DisplayVersion
```

---

## Privilege Escalation

### Common Checks
```cmd
# Check current privileges
whoami /priv
whoami /groups

# Check for AlwaysInstallElevated
reg query HKLM\SOFTWARE\Policies\Microsoft\Windows\Installer\AlwaysInstallElevated
reg query HKCU\SOFTWARE\Policies\Microsoft\Windows\Installer\AlwaysInstallElevated

# Check for stored credentials
cmdkey /list

# Check for saved WiFi passwords
netsh wlan show profiles
netsh wlan show profile name="<SSID>" key=clear
```

### PowerShell Privesc
```powershell
# Check for misconfigured services
Get-WmiObject -Class Win32_Service | Where-Object {$_.StartMode -eq 'Auto' -and $_.State -ne 'Running'}

# Check for weak service permissions
# Requires PowerUp.ps1
. .\PowerUp.ps1
Invoke-AllChecks

# WinPEAS
. .\winPEASany.exe

# Sherlock
Import-Module .\Sherlock.ps1
Find-AllVulns
```

---

## Interesting Files & Locations

```cmd
# User directories
dir C:\Users\ /b
dir C:\Users\<username>\Desktop
dir C:\Users\<username>\Documents
dir C:\Users\<username>\Downloads
dir C:\Users\<username>\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt

# Common config locations
type C:\Windows\System32\drivers\etc\hosts
type C:\Windows\System32\drivers\etc\networks
type C:\Windows\Panther\Unattend\Unattended.xml
type C:\Windows\Panther\Unattend\Autounattend.xml
type C:\Windows\sysprep\sysprep.inf
type C:\Windows\sysprep\sysprep.xml
type C:\Windows\System32\config\AppEvent.Evt

# IIS configs
type C:\inetpub\wwwroot\web.config
type C:\Windows\Microsoft.NET\Framework64\v4.0.30319\Config\web.config

# Database files
where /r C:\ *.mdf
where /r C:\ *.ldf
where /r C:\ *.sqlite
where /r C:\ *.db

# Backup files
where /r C:\ *.bak
where /r C:\ *.old
where /r C:\ *.backup

# Log files
type C:\Windows\System32\winevt\Logs\Security.evtx
type C:\Windows\System32\winevt\Logs\System.evtx
type C:\Windows\System32\winevt\Logs\Application.evtx

# SAM and SYSTEM (requires SYSTEM privileges)
reg save HKLM\SAM C:\sam.dump
reg save HKLM\SYSTEM C:\system.dump
```

---

## PowerShell Enumeration

```powershell
# Execution policy
Get-ExecutionPolicy
Get-ExecutionPolicy -List

# Modules
Get-Module
Get-Module -ListAvailable

# History
Get-History
(Get-PSReadlineOption).HistorySavePath
Get-Content (Get-PSReadlineOption).HistorySavePath

# Variables
Get-Variable
Get-ChildItem Env:

# Functions
Get-ChildItem Function:\

# Aliases
Get-Alias

# Transcripts
Get-ChildItem C:\Users\*\Documents\PowerShell_transcript*.txt -ErrorAction SilentlyContinue
```

---

## WMI Queries

```powershell
# System
Get-WmiObject -Class Win32_ComputerSystem
Get-WmiObject -Class Win32_OperatingSystem
Get-WmiObject -Class Win32_Processor
Get-WmiObject -Class Win32_BIOS

# Storage
Get-WmiObject -Class Win32_LogicalDisk
Get-WmiObject -Class Win32_DiskDrive

# Network
Get-WmiObject -Class Win32_NetworkAdapterConfiguration | Where-Object {$_.IPEnabled -eq $true}
Get-WmiObject -Class Win32_NetworkAdapter | Where-Object {$_.NetEnabled -eq $true}

# Users
Get-WmiObject -Class Win32_UserAccount
Get-WmiObject -Class Win32_Group

# Processes
Get-WmiObject -Class Win32_Process | Select-Object Name, ProcessId, CommandLine

# Services
Get-WmiObject -Class Win32_Service | Select-Object Name, State, StartMode, PathName

# Event logs
Get-WmiObject -Class Win32_NTLogEvent -Filter "Logfile = 'Security'" | Select-Object -First 10
```

---

## 🔧 One-Liners

```cmd
# Quick system overview
systeminfo && whoami /all && net user && net localgroup administrators

# Find all interesting files
where /r C:\ *.txt *.config *.xml *.ini *.log *.bak *.old 2>nul

# Quick network overview
ipconfig /all && netstat -ano && route print
```

```powershell
# Comprehensive enumeration script
Get-ComputerInfo; Get-LocalUser; Get-LocalGroupMember -Group "Administrators"; Get-Process; Get-Service | Where-Object {$_.Status -eq 'Running'}
```

---
