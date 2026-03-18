## 2026-03-18 - 🛡️ Sentinel: [HIGH] Strengthen JWT cookie (Secure + SameSite=Strict)
**Vulnerability:** The application was setting cookies for `access_token`, `device_id`, and `teacher_code` with `samesite="lax"` and missing the `Secure` flag. This left the application more vulnerable to Cross-Site Request Forgery (CSRF) and allowed cookies to be transmitted over unencrypted HTTP connections.
**Learning:** The FastAPI `response.set_cookie` method defaults to lax security if not explicitly configured otherwise.
**Prevention:** Always set `secure=True` and `samesite="strict"` when setting sensitive cookies like authentication tokens or session identifiers.
