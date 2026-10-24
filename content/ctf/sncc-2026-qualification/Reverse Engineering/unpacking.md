---
title: Unpacking
slug: unpacking
category: Reverse Engineering
author: Arman Abrahamyan
tags: [reverse-engineering, upx, packer, elf]
description: A UPX-packed ELF leaks only fragments of the flag to strings. Decompressing it properly reveals the full flag, hidden among filler strings.
---

The ELF is packed with **UPX** - that's why `file` shows no section headers and calls it statically linked. `upx -d` restores the original, and the flag sits as a plaintext string in `.data`, hidden among 80 copies of a filler string so a casual `strings` scroll walks straight past it.
`file` flags something unusual right away:
```bash
file rev_unpacking/unpacking

ELF 64-bit LSB pie executable, x86-64, statically linked, no section header
```
Two tells: `no section header` (a normal compiler never emits this - packers drop sections to break static tooling) and `statically linked` (the real program's dynamic linkage is hidden underneath). `readelf -S` confirms there's nothing to analyse statically:
```bash
readelf -S rev_unpacking/unpacking

There are no sections in this file.
```
Which packer? The magic and banner say UPX 4.01:
```bash
strings rev_unpacking/unpacking | grep -i upx

UPX!
$Info: This file is packed with the UPX executable packer http://upx.sf.net $
$Id: UPX 4.01 Copyright (C) 1996-2022 the UPX Team. All Rights Reserved. $
```
`UPX!` is the literal magic that marks the start and end of UPX's packed header.
Running `strings` on the packed file already leaks fragments of the flag:
```bash
strings rev_unpacking/unpacking | grep -A1 'HTB{'

HTB{T6-Ultimat
n-cker}
```
But you can't just guess the rest. UPX compression replaces repeated substrings with back-references to earlier output, so bytes appearing for the first time survive verbatim while anything matchable against earlier data becomes a length/distance pair which is why the flag comes through with holes (`T6-Ultimat` … `n-cker`). Decompress properly instead
UPX is symmetric so the same tool decompresses. Work on a copy, since `upx -d` rewrites the file in place:
```bash
cp unpacking unpacking.unpacked
upx -d unpacking.unpacked
strings -a unpacking.unpacked | grep -oE 'HTB\{[^}]*\}'

HTB{The-Ultimate-Elf-Unpacker}
```
