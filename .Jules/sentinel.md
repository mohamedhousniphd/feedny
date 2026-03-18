# Security Learnings

## XSS (Cross-Site Scripting)

* Dynamically injecting data into HTML templates without proper escaping leaves the application vulnerable to Cross-Site Scripting (XSS).
* Specifically, for Reflected XSS, ensure any user-provided data such as tokens and query parameters are properly sanitized before replacement.
* Always use `html.escape()` when dealing with variables embedded in HTML content. Cast variables to string prior to escaping.

## Shadowing Built-in Modules

* When naming variables in your code, specifically dealing with HTML templates, avoid using the variable name `html`. This name shadows the built-in `html` library in Python (`import html`). Use names like `html_content` instead to avoid shadowing built-in functions.