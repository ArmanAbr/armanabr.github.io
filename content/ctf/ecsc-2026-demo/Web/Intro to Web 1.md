---
difficulty: Intro
author: W4RUM
---

### Description
You've never touched web hacking before? You want to know what actually happens when you hit Enter in your browser's address bar? You want to learn about all the things that happen in the background while you're seeing this rather boring bit of text on your screen?
Then this challenge is for you.
Prepare yourself, for the web is vast and full of errors.
### Walkthrough
The first part of the flag is in the source code of the website in line 62.
```
CSCG{access_granted_
```
To get the second part of the flag we need to bypass the timer, it works the way that when it hits **0** it will give us the flag.
```js
countDownTime = 10000;

function countDown() {
    countDownTime--;
    if (countDownTime > 0) {
        document.getElementById("flag-timer").innerHTML = countDownTime;
    } else {
        clearInterval(countDownIntervalId);
        document.getElementById("flag-button").innerHTML = ""+
            '<a href="." onClick="showFlag();return false;">Show flag!</a>';
    }
}

function showFlag() {
	const randomGenerator = mulberry32(0x533d);
	const flag = Math.floor(randomGenerator() * 10000000000).toString(16);
	alert(`Here's the second part of your flag: ${flag}`);
}
```
To bypass it we need to go to the the console and edit the variable countDownTime and set it to 0.
```js
countDownTime=0
```
Clicking the button then runs showFlag() and gives the second part:
```
e7e768b0
```
Now for the third part of the flag let's open Burp Suite and look at the HTTP Response Headers.
```
FlagPart3: _to_the_next_level}
```
### Full flag
```
CSCG{access_granted_e7e768b0_to_the_next_level}
```