## 2026-03-18 - 🛡️ Sentinel: [HIGH] Strengthen JWT cookie (Secure + SameSite=Strict)
**Vulnerability:** The application was setting cookies for `access_token`, `device_id`, and `teacher_code` with `samesite="lax"` and missing the `Secure` flag. This left the application more vulnerable to Cross-Site Request Forgery (CSRF) and allowed cookies to be transmitted over unencrypted HTTP connections.
**Learning:** The FastAPI `response.set_cookie` method defaults to lax security if not explicitly configured otherwise.
**Prevention:** Always set `secure=True` and `samesite="strict"` when setting sensitive cookies like authentication tokens or session identifiers.

---
**CORS Security:** CORS with credentials must not use a wildcard. Use environment variables to dynamically allow specific origins, falling back to an empty list (most restrictive) for secure defaults.

---
# Security Learnings

## XSS (Cross-Site Scripting)
- Always sanitize dynamic variables injected into HTML templates using `html.escape()` to prevent Reflected Cross-Site Scripting (XSS).
- Specifically, for Reflected XSS, ensure any user-provided data such as tokens and query parameters are properly sanitized before replacement.
- Always cast variables to string prior to escaping: `html.escape(str(variable))`.

## Shadowing Built-in Modules
- When naming variables in your code, specifically dealing with HTML templates, avoid using the variable name `html`. This name shadows the built-in `html` library in Python (`import html`). Use names like `html_content` instead to avoid shadowing built-in functions.
