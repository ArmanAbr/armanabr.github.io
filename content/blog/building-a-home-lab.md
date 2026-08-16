---
title: Building a Home Lab That Actually Teaches You Something
slug: building-a-home-lab
date: 2026-07-28
tags: [Home Lab, Active Directory, Methodology, Windows, Learning]
description: A practical, low-cost home lab layout for practising Active Directory and web attacks — what to install, how to segment it, and what to break first.
---

Boxes on HackTheBox teach you *techniques*. A home lab teaches you *why they
work* — because you built the vulnerable thing yourself and watched it fall
over. Here's the setup I actually use.

## The minimum viable lab

You do not need a rack. Three VMs on a single laptop with 16 GB of RAM is
enough to start:

1. **Attacker** — Kali or Parrot.
2. **Domain Controller** — Windows Server 2019 evaluation (180-day free).
3. **Domain-joined workstation** — Windows 10/11 evaluation.

Put them all on a **host-only / internal network** so nothing you do leaks onto
your real LAN.

!!! danger "Isolate it"
    A deliberately vulnerable lab is, by definition, a soft target. Never bridge
    these VMs to your home network or the internet. Host-only networking is the
    default rule, not a nice-to-have.

## Making the AD lab vulnerable *on purpose*

A clean domain teaches you nothing. Seed it with the misconfigurations you want
to practise attacking. The fastest way is a script that plants them for you:

```powershell
# GOAD (Game of Active Directory) builds a fully vulnerable multi-domain
# forest with Kerberoastable accounts, ACL abuse paths, and more.
git clone https://github.com/Orange-Cyberdefense/GOAD
```

If you'd rather learn by hand, plant these one at a time and attack each before
moving on:

- A **Kerberoastable** service account (set an SPN on a user).
- An **AS-REP roastable** account (disable Kerberos pre-auth on a user).
- A juicy **ACL** — give a low-priv user `GenericAll` over a group.
- A password reused across the workstation local admin and a domain account.

## A first afternoon

Once it's standing, run the exact loop you'd run on an engagement:

```bash
# 1. Enumerate the domain from the attacker VM
nxc smb 10.10.10.0/24
nxc ldap DC01.lab.local -u alice -p Password123 --users

# 2. Roast what you can
impacket-GetUserSPNs lab.local/alice:Password123 -dc-ip 10.10.10.10 -request

# 3. Map paths
bloodhound-python -u alice -p Password123 -d lab.local -ns 10.10.10.10 -c All
```

Then open BloodHound and trace a path from `alice` to `Domain Admins`. When you
find one, walk it. When you're done, **rebuild the box from a snapshot** and do
it again faster.

## Why this beats grinding boxes alone

Public boxes hide the defender's view. In your own lab you can:

- Open **Event Viewer** on the DC and watch which of your attacks generate
  which Event IDs (4768, 4769, 4624…). This is how you start thinking like blue
  team.
- Toggle a mitigation, re-run the attack, and *see* it fail.
- Break things with zero fear of a shared environment or a rate limit.

Grinding boxes makes you faster. Building the lab makes you *understand*. Do
both — but if you only have time for one this month, build the lab.
