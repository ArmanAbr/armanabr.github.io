---
title: Challenge Template
slug: htb-challenge-template
kind: Challenge
category: Web
date: 2026-09-25
platform: HackTheBox
difficulty: Easy
points: 30
tags: [hackthebox, retired, jwt, source-review]
description: Copy this file to start a HackTheBox challenge writeup - it shows every field a challenge uses.
path:
  - Read the source
  - Find the bug
  - Flag
draft: true
---

# How to use this file

Copy it to `content/writeups/htb-<name>.md`, change the frontmatter, write the
body, then delete `draft: true` so it publishes.

## The fields a challenge uses

- `kind: Challenge` puts it under **Type -> Challenge** on the writeups page.
  Machines need nothing (they are the default); Sherlocks use `kind: Sherlock`.
- `category:` replaces `os:` - Web, Pwn, Crypto, Reverse Engineering, Forensics,
  Misc, Hardware, Mobile, Blockchain, OSINT, Game Hacking. Spelling is flexible:
  `rev`, `reversing` and `reverse engineering` all become "Reverse Engineering".
- No `os:` line. Challenges show `Challenge · Web` where machines show `Windows`.
- `image:` looks in `static/challenges/` first, then `static/machines/`. Without
  one, the card shows the first two letters of the title instead.
- `path:` renders as the numbered chain at the top. On a challenge it is titled
  **Solution path** rather than Attack path.
- `points:`, `difficulty:`, `tags:` and `description:` work exactly as they do on
  a machine writeup. Keep the description under ~160 characters so Google shows
  all of it.

## Writing the body

Start sections at `#` like the other writeups - they are shifted down a level
automatically, so the contents box on the right keeps its structure.

```bash
echo 'commands look like this'
```

> [!note]
> Obsidian-style callouts render as note boxes.
