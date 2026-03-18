## Description

🎯 **What:** The vulnerability fixed was an overly permissive CORS configuration that allowed any origin (`["*"]`) while also allowing credentials (`allow_credentials=True`).
⚠️ **Risk:** If left unfixed, this exposes the application to Cross-Site Request Forgery (CSRF) and cross-origin data theft, as malicious sites could make authenticated requests on behalf of users.
🛡️ **Solution:** The fix replaces the hardcoded `["*"]` wildcard with a dynamic configuration that reads the `ALLOWED_ORIGINS` environment variable, splits it into a list, and uses it for the `CORSMiddleware`. This allows administrators to specify an exact list of allowed origins or fall back to an empty list (most restrictive) if unset.