# Security Learnings

## Hardcoded Default Secret Keys

**Vulnerability:**
Using a static default fallback for sensitive material, such as a JWT `SECRET_KEY` (e.g., `os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")`), introduces a severe risk. If the application is deployed to production without properly configuring the environment variable, the predictable default key is used. Attackers can then forge authentication tokens and gain unauthorized access to any account, or even escalate privileges to admin.

**Resolution:**
The hardcoded fallback was removed. Instead, a dynamically generated random key using `secrets.token_urlsafe(32)` acts as the default if the environment variable is not provided. This ensures that even if developers forget to set the environment variable, the application still uses a highly secure, non-guessable key, preventing malicious actors from forging tokens based on a known default string.
