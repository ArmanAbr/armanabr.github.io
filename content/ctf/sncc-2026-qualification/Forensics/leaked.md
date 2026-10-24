---
title: Leaked
slug: leaked
category: Forensics
author: Arman Abrahamyan
tags: [forensics, memory-forensics, volatility, linux, msfvenom, reverse-shell]
description: A Linux memory dump worked with Volatility 2: find the hand-run reverse shell, carve it out of the page cache, and crack the leaked password.
---

The profile is a **Vol2** profile (Vol3 uses a different symbol format), so it drops into Vol2's Linux overlays folder. After that, one alias keeps every command short:
```bash
cp Ubuntu_4.15.0-184-generic_profile.zip ~/volatility/volatility/plugins/overlays/linux/

vol2 --info | grep -i linux

PROFILE=LinuxUbuntu_4_15_0-184-generic_profilex64
VOL="vol2 -f memory.dmp --profile=$PROFILE"
```
## Q1 - Who logged in, and when?
`linux_psaux` shows what processes are running on the system.
```bash
$VOL linux_pslist
$VOL linux_psaux   

1439  1000  1000  sshd: developer@pts/0
1440  1000  1000  -bash
1521  1000  1000  ./jN8ziHXGE
```
`linux_pslist` puts the `developer` SSH session and bash starting at `2022-12-08 15:21` UTC.
**Answer:** `developer 2022-12-08 15:21`
## Q2 - IP of the enp0s3 interface
```bash
$VOL linux_ifconfig

enp0s3   192.168.1.5   08:00:27:3f:7a:8c   False
```
**Answer:** `192.168.1.5`
## Q3 - the suspicious process ID
That odd `./jN8ziHXGE` is a binary in the developer's home and is PID **1521**, and its parent is bash (PID 1440), so the user ran it by hand.
**Answer:** `1521`
## Q4 - When was the malware executed?
```bash
$VOL linux_bash

1440 bash 2022-12-08 15:21:43 UTC  pwd
1440 bash 2022-12-08 15:21:52 UTC  ls
1440 bash 2022-12-08 15:22:03 UTC  ./jN8ziHXGE
```
**Answer:** `15:22:03`
## Confirming it's malware - the C2 connection
```bash
$VOL linux_netstat

TCP 192.168.1.5:39112  77.74.198.52:4444  ESTABLISHED  jN8ziHXGE/1521
```
PID 1521 holds an established connection to **77.74.198.52:4444**. Port 4444 so it's likely a reverse shell.
## Carving the binary
Confirm the mapping, find the file's inode in the page cache, then dump the bytes straight out of memory, no disk image needed:
```bash
$VOL linux_proc_maps -p 1521
# /home/developer/jN8ziHXGE
$VOL linux_find_file -F /home/developer/jN8ziHXGE
# 0xffff96f73c532328
$VOL linux_find_file -i 0xffff96f73c532328 -O jN8ziHXGE.bin
file jN8ziHXGE.bin
# ELF 64-bit, statically linked, no sections, 250 bytes
```
A 250-byte, statically-linked, RWX ELF with no section headers is very likely **msfvenom** shellcode. The syscall stubs (`socket`/`connect`/`dup2`/`execve`) plus the embedded IP and port (`77.74.198.52`, `0x115c` = 4444) confirm a `linux/x64/shell_reverse_tcp` payload.
```bash
md5sum    jN8ziHXGE.bin   # 853bcc7d0867474ce3ab28ecb9756276
sha256sum jN8ziHXGE.bin   # a8a037792b3f1d2a9bd0dba47be618631d4c015ec2fd488bc88cca5f326bfc23
```
## The leaked password
Recover `/etc/passwd` and `/etc/shadow` the same way (`find_file -F` for the inode, `-i` to dump), then crack the hash:
```bash
$VOL linux_find_file -F /etc/shadow
$VOL linux_find_file -i <inode> -O shadow.txt
john --format=sha512crypt --wordlist=/usr/share/wordlists/rockyou.txt hash.txt
# developer:developer
```
The `developer` account's password was just `developer` - exactly the kind of weak credential that ends up leaked.
## Answers 5-10

| Q5  | Malware path       | `/home/developer/jN8ziHXGE`                                        |
| --- | ------------------ | ------------------------------------------------------------------ |
| Q6  | C2                 | `77.74.198.52:4444`                                                |
| Q7  | Malware MD5        | `853bcc7d0867474ce3ab28ecb9756276`                                 |
| Q8  | Malware SHA256     | `a8a037792b3f1d2a9bd0dba47be618631d4c015ec2fd488bc88cca5f326bfc23` |
| Q9  | Malware type       | `linux/x64/shell_reverse_tcp`                                      |
| Q10 | Developer password | `developer`                                                        |
