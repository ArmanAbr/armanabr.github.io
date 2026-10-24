---
title: Iron Window
slug: iron-window
category: Reverse Engineering
author: Arman Abrahamyan
tags: [reverse-engineering, pyinstaller, python, bytecode, marshal]
description: A PyInstaller binary whose payload builds the flag, then XOR-encodes it as a decoy. Replaying the emit() constants recovers the pre-XOR flag.
---

Identify the container using `file` and `strings`
```bash
$ file rev_iron_window/iron_window

ELF 64-bit LSB executable, x86-64, dynamically linked, stripped

$ strings -n 6 iron_window | grep -iE 'pyinstaller|libpython|_MEIPASS'

libpython3.10.so.1.0
Could not load PyInstaller's embedded PKG archive from the executable (%s)
_MEIPASS
```
So it's PyInstaller with an embedded CPython 3.10. Plan: unpack the CArchive appended to the ELF, pull out the entry-point script, and read its bytecode.
Disassembling the recovered `final1` code object shows five top-level functions:
`_payload` is the target. It fills a `values` list through a helper:
```python
def emit(base, delta, count):
    x = base
    for _ in range(count):
        x += delta          # == base + delta * count
    values.append(x)
```
then makes 43 calls with hardcoded constants (`emit(60, 1, 12)`, `emit(70, 1, 14)`, …) and ends with what looks like an encoding pass:
```python
encoded = [v ^ 32 for v in values]
return marshal.dumps(tuple(encoded))
```
That tail is the trap. `v ^ 32` is an ASCII case-flip; applying it turns the flag into the mangled `htb[whyhvntthughtbutthbfr]`. The **pre-XOR** `values` are already the flag's ASCII bytes  -  `emit(60, 1, 12)` -> `72` -> `'H'`. So the solve is just to replay the `emit()` constants and skip the encoding entirely.
## Solution
```python
#!/usr/bin/env python3
import struct, zlib
import xdis.magics as M
from xdis.unmarshal import load_code

BIN = "rev_iron_window/iron_window"
data = open(BIN, "rb").read()

COOKIE = b"MEI\x0c\x0b\x0a\x0b\x0e"
pos = data.rfind(COOKIE)
_, pkglen, toc_off, toc_len, pyver = struct.unpack("!8sIIII", data[pos:pos + 24])
arc = pos + 24 + 64 - pkglen
print(f"[+] PyInstaller archive @ {arc:#x}, python {pyver // 100}.{pyver % 100}")

entries, p, end = {}, arc + toc_off, arc + toc_off + toc_len
while p < end:
    (elen,) = struct.unpack("!i", data[p:p + 4])
    off, csize, usize, flag, typ = struct.unpack("!IIIBc", data[p + 4:p + 18])
    name = data[p + 18:p + elen].rstrip(b"\0").decode()
    blob = data[arc + off:arc + off + csize]
    entries[name] = zlib.decompress(blob) if flag else blob
    p += elen
print(f"[+] {len(entries)} entries: {', '.join(entries)}")

magic_int = struct.unpack("<H", M.magics["3.10"][:2])[0]
co = load_code(entries["final1"], magic_int)

payload = next(c for c in co.co_consts
               if hasattr(c, "co_code") and c.co_name == "_payload")

code, consts = payload.co_code, payload.co_consts
values, window = [], []
for i in range(0, len(code), 2):
    op, arg = code[i], code[i + 1]
    if op == 100:
        window.append(consts[arg])
    elif op == 131 and arg == 3:
        base, delta, count = window[-3:]
        values.append(base + delta * count)
        window.clear()
    elif op != 124:
        window.clear()

flag = "".join(map(chr, values))
print(f"[+] recovered {len(values)} emit() calls")
print(f"[+] decoy (v ^ 32): {''.join(chr(v ^ 32) for v in values)}")
print(f"\nFLAG: {flag}")
```
Output:
```
[+] PyInstaller archive @ 0xf2d9, python 3.10
[+] 11 entries: struct, pyimod01_archive, pyimod02_importers, pyimod03_ctypes,
    pyiboot01_bootstrap, pyi_rth_inspect, final1, libpython3.10.so.1.0,
    pyi-contents-directory _internal, base_library.zip, PYZ.pyz
[+] recovered 43 emit() calls
[+] decoy (v ^ 32): htb[whyhvntthughtbutthbfr]

FLAG: HTB{WHY_H4V3NT_1_TH0UGHT_4B0UT_TH15_B3F0R3}
```
