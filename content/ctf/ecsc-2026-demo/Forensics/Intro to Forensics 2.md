---
difficulty: Easy
author: THEVAMP
---

### Description
We were able to capture a hidden service. Could you recover the secret order?
### Walkthrough
We're given a single capture, `intro-forensics-2.pcapng`, so the flag is hidden somewhere in the traffic.
```bash
tshark -r intro-forensics-1.pcapng -q -z io,phs
```
There are only two protocols: 42 HTTP frames and 32 raw `data` frames.
- **HTTP:** 21 `GET /watch?v=<id>` requests to `www.youtube.com`, each answered with an empty `301` (`Content-Length: 0`). There's nothing useful here.
- **Data:** every connection goes to one non-YouTube host, `45.142.177.160`, and they are all byte-identical. The client sends `|<|\|0<|<|<|\|0<|<`, which reads as "knock knock".
The payloads are all the same, so they can't carry the flag. The only thing that changes between connections is the **destination port**.
```bash
tshark -r intro-forensics-2.pcapng \
  -Y "ip.dst == 45.142.177.160 && tcp.flags.syn == 1" \
  -T fields -e tcp.dstport
```
Output:
```
17235 17223 31595 28208 25451 26990 26463 28526
24424 25953 30309 28275 24420 12336 12402 32010
```
A port is 16 bits, so each one is converted to 2 big-endian bytes and the bytes are decoded as ASCII:
```python
ports = [17235, 17223, 31595, 28208, 25451, 26990, 26463, 28526, 24424, 25953, 30309, 28275, 24420, 12336, 12402, 32010]

print(b"".join(p.to_bytes(2, "big") for p in ports).decode().strip())
```
### Flag
```
CSCG{kn0cking_on_heavens_d000r}
```