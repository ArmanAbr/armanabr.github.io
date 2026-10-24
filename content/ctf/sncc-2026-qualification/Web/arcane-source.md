---
title: Arcane Source
slug: arcane-source
category: Web
author: Arman Abrahamyan
tags: [web, source-review]
description: A quick web warmup: the flag was sitting in the page source.
---

# The flag

A warmup web challenge. Nothing clever needed - the flag was left in the page's
source code, so viewing source (or `curl`-ing the page) was enough:

```bash
curl -s http://<target>/ | grep -o 'HTB{[^}]*}'
```
