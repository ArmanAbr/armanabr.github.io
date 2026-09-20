---
difficulty: Intro
author: W4RUM
---

### Description
Now that you have a rough grasp on the things you can do with just your browser, let's take a closer look at how to utilize HTTP request manipulation with ZAP.
### Walkthrough
After opening the document, it says:
```
For sEcUrItY rEaSoNs, you need to update your system to Windows 95 before accessing this website!
```
That means that we need to change our `User-Agent` so it says that i am on Windows 95, not Linux. We can do that in many ways, for example intercept the http request with Burp Suite and change the `User-Agent` header, and we can also use a browser extension called `User-Agent Switcher` and set it to `User-Agent: Mozilla/4.0 (compatible; MSIE 5.5; Windows 95)`.
After reloading the page we can see that it is revealing the first part of the flag which is:
```
CSCG{1334k_
```
Now for the second part of the flag, we need to use Burp's Intercept when the website submits a form, and we can see in the request, that there is a parameter called `filename` which we can modify to `filename=flag.txt`. And now we have the second part of the flag.
```
1nt3rc3pt_
```
To get the third part of the flag we need to do the same thing but with a GET request.
```js
GET /read-file.php?filename=flag.txt HTTP/1.1
```
And now we have the third part of the flag.
```
m0d1fy_fwd_
```
And lastly for the fourth and last part of the flag we need to access the document that has the flag, but the problem is that if you are not authorized, the flag gets burnt before you access it.
```
The last part of the flag is hidden here. Come back here after clicking on the link if you need help. 
```
So to bypass it we need to intercept the request that gets sent after clicking the link, and modify the `authorized` parameter and set it to `true`.
```js
GET /burn-after-reading-6414009.php?authorized=true HTTP/1.1
```
And here is the last part of the flag obtained.
```
r3p34t}
```
### Full flag
```
CSCG{1334k_1nt3rc3pt_m0d1fy_fwd_r3p34t}
```