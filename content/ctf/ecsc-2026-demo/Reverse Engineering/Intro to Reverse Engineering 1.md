---
difficulty: Easy
author: 0X4D5A
---

### Description
Let's have a gentle introduction to reverse engineering x86_64 binaries on Linux. You can find a detailed writeup with many basics and solutions to this challenge attached :)
### Walkthrough
We are given a linux binary called `rev1`. I'll decompile it using `ghidra`. After doing so i could see a very readable `main` function.
```c
undefined8 main(void)
{
  int iVar1;
  ssize_t sVar2;
  char local_38 [44];
  int local_c;
  
  initialize_flag();
  puts("Give me your password: ");
  sVar2 = read(0,local_38,0x1f);
  local_c = (int)sVar2;
  local_38[local_c + -1] = '\0';
  iVar1 = strcmp(local_38,"m4gic_passw0rd");
  if (iVar1 == 0) {
    puts("Thats the right password!");
    printf("Flag: %s",flagBuffer);
  }
  else {
    puts("Thats not the password!");
  }
  return 0;
}
```
The binary reads your password input, removes the new line and compares it with `m4gic_passw0rd`.
So we can just submit this password in the remote server and get the flag.
```js
ncat --ssl-verify cbx45jatylfvbb7ij3ytepyqh2-main-1024-intro-rev-1.ecsc.jetzt 443
```
### Flag
```
CSCG{congrats_t0_y0ur_(maybe?)_f1rst_r3versing_t4sk}
```