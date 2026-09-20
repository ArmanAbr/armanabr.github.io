---
difficulty: Easy
author: 0X4D5A
---

### Description
What is this non(c/s)ence everyonce is taking about?
### Walkthrough
We are given a python script: `main.py` which is a small AES-CTR encryption service:
```python
secret_key = os.urandom(16)

def encrypt(plaintext, counter):
    m = hashlib.sha256()
    m.update(counter.to_bytes(8, byteorder="big"))

    alg = AES.new(secret_key, AES.MODE_CTR, nonce=m.digest()[0:8])
    ciphertext = alg.encrypt(plaintext)

    return ciphertext.hex()
```
The service lets us send one plaintext, which it encrypts 256 times: once for each counter value from 0 to 255. It then encrypts the flag using a random one-byte counter.
That counter isn't random enough, because it can only take 256 values. The flag must therefore have been encrypted with one of the 256 counters we can already make the service use.
In CTR mode, encryption is just:
```
ciphertext = plaintext XOR keystream
```
So if we send a plaintext made entirely of zero bytes, each returned ciphertext is the keystream itself `(0 XOR k = k)`. The plaintext just needs to be at least as long as the flag, so we send 128 zero bytes. That gives us all 256 possible keystreams, and we XOR each one with the encrypted flag until the result contains `CSCG{`.
```python
from pwn import *

r = remote("zhnj32aedd5gl4n7k5cw63rvhi-main-1024-intro-crypto-1.ecsc.jetzt", 443, ssl=True)

r.sendlineafter(b"Enter some plaintext (hex): ", b"00" * 128)

keystreams = []
for i in range(256):
    r.recvuntil(f"Ciphertext {i:03d}: ".encode())
    keystreams.append(unhex(r.recvline().strip()))

r.recvuntil(b"Flag: ")
enc_flag = unhex(r.recvline().strip())

for ks in keystreams:
    flag = xor(enc_flag, ks[:len(enc_flag)])
    if b"CSCG{" in flag:
        print(flag.decode())
```
### Flag
```
CSCG{CTR_A3S_Br0ken!???N0pe,it's_C4ll3d_number_used_0nce_f0r_a_r3as0n}
```