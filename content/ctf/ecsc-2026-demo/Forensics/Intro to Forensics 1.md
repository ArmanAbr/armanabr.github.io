---
difficulty: Easy
author: THEVAMP
---

### Description
First we will learn a little bit about Wireshark. For the beginning just start play around with Wireshark and their filters, look into the protocols and getting familiar with the tool. Besides Reverse Engineering skills, recording the network traffic is an important part in the analysis of malware.
### Walkthrough
We are given a packet capture `intro-forensics-1.pcapng` and a remote service that asks us for a valid token. So we need to recover the that token from the captured traffic using Wireshark.
The first thing that stands out is this HTTP request.
```js
POST /login HTTP/1.1
Host: 127.0.0.1:1024
Connection: keep-alive
Content-Length: 134
Cookie: token="MhhWhatToken??"
```
And in the response we can see the token which we can now submit and get the flag.
```js
HTTP/1.1 200 OK
Server: Werkzeug/2.2.3 Python/3.10.12
Date: Mon, 18 Mar 2024 10:54:48 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 57
Set-Cookie: token=0bf77fce4af7f09d7937b59b5dfe8ce4c018ea14cd3b363d12ddc7c670ca045313aa6156b40273390e43e6128d32b993742f09d1cea1db3e3837f6082d3e6932; Path=/
Connection: close

Thx for your request! Please go <a href='/'>home</a> now!
```
### Flag
```
CSCG{sn00py_sn00p_w1th_w1reshark!}
```