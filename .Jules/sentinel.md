# Security Learnings
- Always sanitize dynamic variables injected into HTML templates using `html.escape()` to prevent Reflected Cross-Site Scripting (XSS).
- When importing the `html` module, rename any local variables named `html` (e.g., to `html_content`) to avoid shadowing the standard library module.
