---
title: "API Security: 10 Mistakes That Still Happen in 2026"
date: 2026-08-07
description: "Despite years of awareness, these API security vulnerabilities continue to show up in production. Here's how to identify and fix them."
tags: ["api-security", "web-security", "best-practices", "2026"]
categories: ["articles"]
author: "Arman Abrahamyan"
---

# API Security: 10 Mistakes That Still Happen in 2026

> APIs are the backbone of modern applications. Unfortunately, they're also the most common attack vector. Despite OWASP's API Security Top 10 being around for years, these mistakes keep surfacing in production codebases.

---

## 1. Broken Object Level Authorization (BOLA)

**The Mistake:** Trusting the client to respect resource boundaries.

```http
GET /api/v1/invoices/12345
Authorization: Bearer <user_token>
```

If the server doesn't verify that invoice `12345` belongs to the authenticated user, any user can access any invoice by changing the ID.

**The Fix:**

```python
# Python (FastAPI)
@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, user: User = Depends(get_current_user)):
    invoice = db.get_invoice(invoice_id)
    if invoice.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return invoice
```

```go
// Go (Gin)
func getInvoice(c *gin.Context) {
    invoiceID := c.Param("id")
    user := c.MustGet("user").(User)

    invoice, err := db.GetInvoice(invoiceID)
    if err != nil || invoice.OwnerID != user.ID {
        c.JSON(403, gin.H{"error": "Access denied"})
        return
    }
    c.JSON(200, invoice)
}
```

---

## 2. Missing Rate Limiting

**The Mistake:** Allowing unlimited requests to sensitive endpoints like login, password reset, or OTP verification.

**The Fix:**

```python
# Python (SlowAPI + Redis)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")
def login(request: Request, credentials: LoginSchema):
    ...
```

```go
// Go (golang.org/x/time/rate)
var limiter = rate.NewLimiter(rate.Every(time.Minute), 5)

func loginHandler(w http.ResponseWriter, r *http.Request) {
    if !limiter.Allow() {
        http.Error(w, "Too many requests", 429)
        return
    }
    // ...
}
```

---

## 3. Excessive Data Exposure

**The Mistake:** Returning entire database objects instead of DTOs.

```json
// ❌ DON'T: Returning raw DB object
{
  "id": 42,
  "username": "alice",
  "email": "alice@example.com",
  "password_hash": "$2b$12$...",
  "ssn": "123-45-6789",
  "internal_notes": "Flagged for review"
}
```

**The Fix:**

```python
# Python (Pydantic response model)
class UserPublic(BaseModel):
    id: int
    username: str
    email: str

@app.get("/users/{user_id}", response_model=UserPublic)
def get_user(user_id: int):
    return db.get_user(user_id)
```

---

## 4. Mass Assignment Vulnerabilities

**The Mistake:** Binding request bodies directly to ORM models without field filtering.

```python
# ❌ DON'T: Direct binding
@app.put("/users/{id}")
def update_user(id: int, user: UserModel):  # UserModel has 'is_admin' field
    db.update(id, user)
    # Attacker can set is_admin=true in the JSON body
```

**The Fix:**

```python
# ✅ DO: Explicit allowlist
class UserUpdate(BaseModel):
    username: Optional[str]
    email: Optional[str]
    # is_admin is intentionally NOT here

@app.put("/users/{id}")
def update_user(id: int, update: UserUpdate):
    db.update(id, update.dict(exclude_unset=True))
```

---

## 5. Weak Authentication Schemes

**The Mistake:** Using API keys in query parameters, or JWTs without proper validation.

```http
# ❌ DON'T: API key in URL
GET /api/data?api_key=sk_live_abc123
```

**The Fix:**

```http
# ✅ DO: Token in Authorization header
GET /api/data
Authorization: Bearer <token>
```

**JWT Validation Checklist:**
- Verify signature with the correct algorithm
- Reject `none` algorithm
- Check `exp` claim
- Validate `iss` and `aud` if applicable
- Use short-lived access tokens + refresh tokens

```python
# Python (PyJWT)
import jwt

try:
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"], audience="my-api")
except jwt.ExpiredSignatureError:
    raise HTTPException(401, "Token expired")
except jwt.InvalidTokenError:
    raise HTTPException(401, "Invalid token")
```

---

## 6. Missing Input Validation

**The Mistake:** Assuming clients will send well-formed data.

**The Fix:** Strict schema validation at the edge.

```python
from pydantic import BaseModel, EmailStr, Field, validator

class CreateUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, regex=r"^[a-zA-Z0-9_]+$")
    email: EmailStr
    age: int = Field(..., ge=13, le=120)

    @validator("username")
    def no_reserved_names(cls, v):
        if v.lower() in {"admin", "root", "api"}:
            raise ValueError("Reserved username")
        return v
```

---

## 7. Insecure Direct File Access

**The Mistake:** Using user input to construct file paths.

```python
# ❌ DON'T: Path traversal waiting to happen
@app.get("/download")
def download(filename: str):
    return FileResponse(f"/var/files/{filename}")
    # ?filename=../../../etc/passwd
```

**The Fix:**

```python
from pathlib import Path

@app.get("/download")
def download(filename: str):
    base = Path("/var/files").resolve()
    target = (base / filename).resolve()

    if not target.is_relative_to(base):
        raise HTTPException(400, "Invalid path")

    return FileResponse(target)
```

---

## 8. Missing Security Headers

**The Fix:** Add these headers to all API responses:

```python
# Python (FastAPI middleware)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=63072000"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response
```

---

## 9. Unencrypted Sensitive Data in Transit

**The Mistake:** Serving APIs over HTTP or using weak TLS configurations.

**The Fix:**
- Enforce TLS 1.2+
- Use HSTS
- Pin certificates if applicable for mobile clients
- Never send credentials or tokens over HTTP

---

## 10. Insufficient Logging & Monitoring

**The Mistake:** Only logging errors, not security-relevant events.

**What to Log:**
- Authentication attempts (success & failure)
- Authorization failures (BOLA attempts)
- Input validation failures
- Rate limit hits
- Configuration changes
- File access events

**What NOT to Log:**
- Passwords, tokens, or PII in plaintext
- Full credit card numbers
- Session identifiers

```python
import structlog

logger = structlog.get_logger()

@app.post("/login")
def login(credentials: LoginSchema):
    user = authenticate(credentials)
    if not user:
        logger.warning(
            "auth_failed",
            username=credentials.username,
            ip=request.client.host,
            reason="invalid_credentials"
        )
        raise HTTPException(401, "Invalid credentials")

    logger.info("auth_success", user_id=user.id, ip=request.client.host)
    return {"token": create_token(user)}
```

---

## Quick Reference: API Security Checklist

| Area | Check |
|------|-------|
| Authentication | Strong schemes, short-lived tokens, secure storage |
| Authorization | BOLA checks on every endpoint |
| Input | Strict validation, parameterized queries |
| Output | DTOs only, no raw DB objects |
| Rate Limiting | Per-endpoint, per-user, per-IP |
| Transport | TLS 1.2+, HSTS, no HTTP fallback |
| Headers | Security headers on all responses |
| Secrets | No hardcoded keys, use vaults |
| Logging | Security events logged, PII excluded |
| Dependencies | Automated scanning (Snyk, Dependabot) |

---

## Conclusion

API security isn't about one big fix — it's about layering defenses. Each of these mistakes represents a real-world breach vector that continues to be exploited. Review your APIs against this list, automate what you can, and treat security as a continuous process, not a one-time checklist.

> **Further Reading:**
> - [OWASP API Security Top 10 2023](https://owasp.org/API-Security/editions/2023/en/0x00-header/)
> - [CWE Top 25 Most Dangerous Software Weaknesses](https://cwe.mitre.org/top25/)
