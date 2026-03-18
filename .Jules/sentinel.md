# Security Fix: Hardcoded SECRET_KEY
Replaced hardcoded fallback `SECRET_KEY` with a dynamically generated secure random string (`secrets.token_hex(32)`) across the codebase. If no environment variable is provided, tokens will be secure but invalidated on process restart, effectively forcing production setups to define `SECRET_KEY` explicitly.
