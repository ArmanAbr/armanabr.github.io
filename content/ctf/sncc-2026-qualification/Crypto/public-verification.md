---
title: Public Verification
slug: public-verification
category: Crypto
author: Arman Abrahamyan
tags: [crypto, jwt, rs256, key-confusion]
description: A JWT gov portal only hands out non-admin tokens, but the handout leaks the RS256 private key, so forging an admin token is one script.
---

## The target
A Flask "gov portal" that hands out JSON Web Tokens (JWTs) as login passes:
- **`/register`** creates an account and issues a token. Every token is minted with `is_admin: False`.
- **`/dashboard`** prints the flag, but only if your token's `is_admin` claim is `True`.
So to get the flag i need to make a user that has `is_Admin=True`. 
## Source code
Inside `crypto/_jwt.py`:
```python
def create_token(username):
    return jwt.encode({'is_admin': False, 'username': username}, privkey, algorithm='RS256')

def check_admin(token):
    try:
        payload = jwt.decode(token, pubkey, algorithms=['RS256'])
        return payload.get('is_admin', False)
    except Exception:
        return False
```
And `views.py` gates the flag on that check:
```python
if not check_admin(token):
    ... redirect ...
return render_template('dashboard.html', secret=open('/flag.txt').read()), 200
```
## Exploitation
So after listing the handout i noticed that they left me the private key, normally they shouldn't have given me it, just the public token to encrypt.
With the signing key in hand, forging an admin token is one script: build a token with the same shape `create_token()` uses but flip `is_admin` to `True`, confirm it passes the server's own check locally, then send it to `/dashboard`.
```python
import sys, re, jwt, requests

PRIV = open('application/privkey.pem', 'rb').read()
PUB  = open('application/pubkey.pem',  'rb').read()

token = jwt.encode({'is_admin': True, 'username': 'admin_forged'}, PRIV, algorithm='RS256')
print('Forged JWT:', token)

payload = jwt.decode(token, PUB, algorithms=['RS256'])
assert payload.get('is_admin') is True
print('Local verify OK:', payload)

if len(sys.argv) > 1:
    base = sys.argv[1].rstrip('/')
    r = requests.get(base + '/dashboard', headers={'Authorization': f'Bearer {token}'})
    m = re.search(r'HTB\{[^}]*\}', r.text)
    print(f'HTTP {r.status_code}')
    print('FLAG:', m.group(0) if m else '(not found)')
```
