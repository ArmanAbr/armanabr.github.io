---
difficulty: Easy
authors: [THEVAMP, DIFF-FUSION]
---

### Description
There is a new variant of a ransomware, messing up my image files. Somebody told me a vital part of forensics is to understand files. Could you help me to recover my image file?
### Walkthrough
We are given a single file called `intro-forensics-3` and i am not sure what file this is.
First when i tried running `file ./intro-forensics-3` it answered `./intro-forensics-3: data`, but the file starts with the PNG signature. Walking the chunks shows why nothing can read it:
```
offset   type   length   crc field
8        IDAT   32768    00000018
...
426158   IHDR   13       00000000
491743   IEND   0         0000001a
622875   cHRM   32       00000001
```
Two things stand out:
- `IHDR` is in the middle of the file and `IEND` is not at the end, so the
  chunk order is scrambled.
- No CRC is valid. Instead every CRC field holds a small number, 0 through
  0x1a (26), and there are exactly 27 chunks. `IHDR` holds 0 and `IEND` holds
  26, so that number is the chunk's original position.
So we can parse the chunks, sort the IDAT chunks by that value, and write a repaired PNG. The useful part of the recovery script looks like this:
```python
import struct, zlib

data = open("intro-forensics-3", "rb").read()

chunks, pos = [], 8
while pos < len(data):
    length, = struct.unpack(">I", data[pos:pos + 4])
    body = data[pos + 4:pos + 8 + length]
    index, = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
    chunks.append((index, body))
    pos += 12 + length

out = b"\x89PNG\r\n\x1a\n"
for _, body in sorted(chunks):
    out += struct.pack(">I", len(body) - 4) + body
    out += struct.pack(">I", zlib.crc32(body) & 0xffffffff)

open("fixed.png", "wb").write(out)
```
And then we can finally open the recovered image which shows the flag.
## Flag
```
CSCG{space_space_spaaaace_space!!!}
```