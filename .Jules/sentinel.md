# Security Patches Learning

- Removed hardcoded default JWT secret key (`dev-secret-key-change-in-production`) which was acting as a fallback for the environment variable `SECRET_KEY`.
- Used the `secrets` module (`secrets.token_urlsafe(32)`) to securely generate a random default secret key, ensuring environments where the `SECRET_KEY` env var is unassigned remain secure against token forging attacks, though sessions are invalidated on restart.
- Avoided adding any new external dependencies and maintained the patch strictly within 50 lines.
