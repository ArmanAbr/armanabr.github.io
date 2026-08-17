---
title: Resume
description: Cybersecurity student focused on offensive security, penetration testing and Active Directory.
---

I'm a cybersecurity student focused on **offensive security** - penetration
testing, Active Directory attack paths, web exploitation and privilege
escalation. I learn by breaking things in the lab and writing up exactly how,
which is what this site is for.

> **Looking for:** internships and junior roles in penetration testing, red
> teaming, or security research. [Get in touch](mailto:armanabrahamyan8080@gmail.com).

## Skills

**Offensive security** - Network & web penetration testing · Active Directory
attacks (Kerberoasting, AS-REP roasting, ACL/DCSync abuse) · Privilege
escalation (Linux & Windows) · Post-exploitation

**Tooling** - Nmap · Burp Suite · Metasploit · BloodHound · Impacket ·
NetExec/CrackMapExec · Hashcat · Wireshark · Ffuf/Gobuster

**Scripting** - Python · Bash · PowerShell

**Platforms** - HackTheBox · TryHackMe · Self-built Active Directory lab

## Education

### High School *(in progress)*
*NPUA High School · expected 2028*


## Certifications

- *OSCP (in progress).*

## Projects

### [Sentinel](https://github.com/ArmanAbr/Sentinel)

- Built a dual-brain privesc engine: a deterministic, offline GTFOBins/HackTricks rule engine that ranks ready-to-run escalation vectors (SUID, sudo, capabilities, dangerous groups, writable system files), with an optional Claude LLM layer that re-prioritizes and combines findings.
- Includes autopwn, an authorization-gated engagement orchestrator that chains real Kali tools (nmap, feroxbuster, nikto, enum4linux-ng, searchsploit) into a prioritized foothold report.
- Safety-first design: read-only by default, execution guarded behind explicit authorization flags, graceful degradation with no API key, and 18 offline tests.

### [AD-Path-Finder](https://github.com/ArmanAbr/AD-Path-Finder) 

- Rebuilt the core of BloodHound to understand how AD rights become attack edges: maps access masks and extended-right GUIDs (GenericAll, WriteDacl, ForceChangePassword, DCSync) into a weighted directed graph.
- Runs Dijkstra shortest-path search from any user to Domain Admin, favoring the fewest abuse steps, and flags quick wins (Kerberoastable, AS-REP roastable, unconstrained delegation, DCSync).
- Clean collector/analyzer split (live LDAP collection via ldap3/impacket → offline analysis), with Graphviz path export and 18 offline tests.

### [SSTI-Exploiter](https://github.com/ArmanAbr/SSTI-Exploiter)

- Built a from-scratch, tplmap-style scanner that distinguishes template evaluation from mere reflection using randomized operands across six delimiter families, eliminating the false positives naïve 7*7 checks produce.
- Fingerprints 11 template engines (Jinja2, Twig, Freemarker, ERB, EJS, etc.) via differential probes, then builds engine-specific RCE payloads with correct quoting, output carving, and a time-based fallback for blind targets.
- Ships with a deliberately vulnerable Flask lab and unit tests to demonstrate the full detect → fingerprint → exploit chain safely on localhost.

### Security writeups & notes *(this site)*
*Ongoing*

- Publish detailed, reproducible HackTheBox writeups and technique notes.
- Built the site's static-site generator and tag system from scratch in Python.

## Internships

### Junior Cybersecurity Engineer - Hexens
*June 2024 – August 2025*

Spent more then a year learning offensive security through practical labs and real-world tooling:

- *Network Security: Traffic analysis with Wireshark and tcpdump; network enumeration and attack simulation with Nmap and Metasploit.*

- *Web Application Security: Completed PortSwigger Academy labs; manually exploited SQL Injection, XSS, LFI, RFI, CSRF, and IDOR using Burp Suite.*
  
- *Active Directory: Practiced LDAP enumeration, BloodHound analysis, and Windows privilege escalation including token impersonation and ACL abuse.*
  
- *Scripting & Automation: Built enumeration and exploitation scripts in Python, Bash, and PowerShell to automate repetitive tasks, parse data, and streamline penetration testing workflows.*
  
- *Penetration Testing: Rooted multiple HackTheBox and TryHackMe machines, documenting full attack chains.*

### Junior Software Engineer - DST
*June 2022 – July 2023*

Built internal business tools and worked with databases:

- *Developed internal business tools in VB.NET, streamlining operational workflows.*
  
- *Designed relational database schemas and authored complex SQL queries for reporting and analytics.*
  
- *Participated in agile ceremonies, peer code reviews, and sprint planning.*
  
## Contact

- **Email** - [armanabrahamyan8080@gmail.com](mailto:armanabrahamyan8080@gmail.com)
- **GitHub** - [https://github.com/ArmanAbr]
- **Twitter** - [https://x.com/aarmcyb]
