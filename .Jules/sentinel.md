
## Security Patch: CWE-798 Hard-coded Credentials in sync_admin_account
- **Issue**: The application used a hardcoded default string 'password123' for the admin account if the TEACHER_PASSWORD environment variable was not set, unconditionally updating it on server startup.
- **Solution**: Updated sync_admin_account to check the environment variable. If missing, it uses secrets.token_urlsafe(16) to generate a secure random password on first run and logs it, while ensuring it no longer overwrites an existing admin password on subsequent startups if the env var is omitted.
- **Learnings**: Avoid hardcoded default passwords for critical accounts. Default fallbacks should be dynamically generated secure secrets or the application should fail to start if required security credentials are missing. Unconditional password resets on startup based on missing variables leads to persistent weak credential exposure.
