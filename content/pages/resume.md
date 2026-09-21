---
title: Resume
heading: Arman Abrahamyan
description: Offensive security student · CTF competitor · Yerevan, Armenia
pdf: static/Arman_Abrahamyan_Resume.pdf
---

[armanabrahamyan8080@gmail.com](mailto:armanabrahamyan8080@gmail.com) ·
[+374 41 224247](tel:+37441224247) ·
[linkedin.com/in/armabrahamyan](https://www.linkedin.com/in/armabrahamyan/) ·
[github.com/ArmanAbr](https://github.com/ArmanAbr) ·
[armanabr.github.io](https://armanabr.github.io/)
{: .resume-contact }

16-year-old offensive security student focused on Active Directory, web
exploitation and privilege escalation. 2nd of 209 in the national student CTF
prequalification, selected for Team Armenia at ECSC 2026, and 14 months as an
offensive security intern at Hexens. Looking for penetration testing
internships and junior roles.

## Competitions

### 2nd of 209 - Students National Cyber Challenge 2026, Prequalification *Sep 2026*

- Individual jeopardy CTF run by ISAA on Hack The Box: 10 challenges across 7
  categories in one 13-hour session, human-only (no AI assistants or automation).
- Solved all 10 (Web, Reversing, Pwn, Forensics, AI/ML, Crypto, OSINT) for
  6,575 points and 3 first bloods.

### Team Armenia - European Cybersecurity Challenge (ECSC) 2026, Bochum *Oct 12-16, 2026*

### Students National Cyber Challenge 2026, Final (team) *Oct 24, 2026*

## Projects

### [AD-Path-Finder](https://github.com/ArmanAbr/AD-Path-Finder) *Python*

- A mini-BloodHound: maps AD rights (GenericAll, WriteDacl, ForceChangePassword,
  DCSync) into a weighted graph and runs Dijkstra from any user to Domain Admin,
  fewest abuse steps first.
- Flags quick wins (Kerberoastable, AS-REP roastable, unconstrained delegation);
  live LDAP collection via ldap3/impacket, Graphviz export, 18 offline tests.

### [SSTI-Exploiter](https://github.com/ArmanAbr/SSTI-Exploiter) *Python*

- Tells real template evaluation apart from reflection with randomized probes
  across six delimiter families, avoiding the false positives of naive `7*7` checks.
- Fingerprints 11 template engines and builds engine-specific RCE payloads, with a
  time-based fallback for blind targets and a vulnerable Flask lab for testing.

### [Sentinel](https://github.com/ArmanAbr/Sentinel) *Python*

- Offline GTFOBins/HackTricks rule engine that ranks ready-to-run privilege
  escalation vectors, with an optional LLM layer that re-prioritises and chains them.
- autopwn chains nmap, feroxbuster, nikto, enum4linux-ng and searchsploit into a
  foothold report; read-only by default, authorization-gated, 18 offline tests.

**Also:** [armanabr.github.io](https://armanabr.github.io/) (writeups site on a Python
static site generator I wrote) · AD-Enum-Toolkit · Pentest-Automation · ESP32-S3
drone radar (C++)

## Experience

### Offensive Security Intern - Hexens *Jul 2024 - Aug 2025 · Yerevan*

- Web application security: OWASP Top 10 and the PortSwigger Web Security
  Academy; exploited SQL injection, XSS, LFI/RFI, CSRF, SSRF and IDOR by hand
  in Burp Suite.
- Active Directory: LDAP enumeration, BloodHound analysis, credential abuse,
  lateral movement, token impersonation and ACL abuse.
- Infrastructure: enumeration and privilege escalation on Linux and Windows
  hosts; traffic analysis in Wireshark and tcpdump.
- Scripting: Python, Bash and PowerShell tooling to automate enumeration and
  parse scan output.

### Software Engineering Intern - Database and Statistics Technology *Jun 2023 - May 2024 · Remote*

- Built internal business tools in VB.NET / .NET Framework.
- Designed MySQL schemas and wrote reporting and analytics queries.
- Tested and debugged REST endpoints in Postman; took part in code review and
  sprint planning.

## Certifications & practice

- **Ethical Hacker** - Cisco Networking Academy, Sep 2026
- **In progress:** HTB CDSA, then HTB CPTS
- **HackTheBox:** Hacker rank · 30+ machines · 110+ challenges · level 61

## Skills

**Offensive** - Web application testing · Active Directory attacks
(Kerberoasting, AS-REP roasting, ACL abuse, RBCD, DCSync) · Linux & Windows
privilege escalation · Memory and log forensics

**Tools** - Burp Suite · Nmap · BloodHound · Impacket · NetExec · Evil-WinRM ·
Metasploit · Hashcat · Volatility · Wireshark · ffuf

**Languages** - Python · Bash · PowerShell · SQL · VB.NET · C++

## Education

### NPUA High School - Mathematics and Computer Science *Sep 2025 - 2028 (expected)*
