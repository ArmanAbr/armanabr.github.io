---
difficulty: Easy
author: 0X4D5A
---

### Description
Somehow the password was encoded and can't be found in plaintext in the binary. Can you still figure out the right password?
### Walkthrough
We are given a linux binary called `rev2`. As we did in the first intro rev challenge, we need to first decompile the binary and look at the `main` function, i'll do so using `Ghidra`. This challenge is kind of similar to the intro rev 1 but the password is not stored as plain text anymore.
```c
undefined8 main(void)
{
  int iVar1;
  ssize_t sVar2;
  char local_38 [40];
  int local_10;
  int local_c;
  
  initialize_flag();
  puts("Give me your password: ");
  sVar2 = read(0,local_38,0x1f);
  local_10 = (int)sVar2;
  local_38[(int)sVar2 + -1] = '\0';
  for (local_c = 0; local_c < local_10 + -1; local_c = local_c + 1) {
    local_38[local_c] = local_38[local_c] + -0x77;
  }
  iVar1 = strcmp(local_38,&DAT_00102020);
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
The program subtracts 119 from every byte of our input and then compares the result with s2. So to recover the original password, we add 119 to each byte of s2 , wrapping around at 256. 
We can find the encoded bytes at `00102020`.
```js
02, EA, 02, E8, FC, FD, BD, FD, F2, EC, E8, FD, FB, EA, F7, FC, EF, B9, FB, F6, EA, FD, F2, F8, F7, 00
```
Now let's decode them with this simple python script:
```python
s2 = bytes([
    0x02, 0xea, 0x02, 0xe8, 0xfc, 0xfd, 0xbd, 0xfd, 0xf2,
    0xec, 0xe8, 0xfd, 0xfb, 0xea, 0xf7, 0xfc, 0xef, 0xb9,
    0xfb, 0xf6, 0xea, 0xfd, 0xf2, 0xf8, 0xf7,
])

passwd = bytes((b + 119) % 256 for b in s2)
print(passwd.decode())
```
And the script gives us: 
```
yay_st4tic_transf0rmation
```
Now let's just submit the password to the remote server and grab the flag.
```js
ncat --ssl-verify qabxyy7oz73pji55hgpcgfe2n5-main-1024-intro-rev-2.ecsc.jetzt 443
```
### Flag
```
CSCG{y0u_just_r3versed_a_st4tic_transf0rmation!}
```