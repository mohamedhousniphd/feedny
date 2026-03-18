import html
xss_payload = "<script>alert('XSS')</script>"
escaped = html.escape(str(xss_payload))
print(f"Original: {xss_payload}")
print(f"Escaped: {escaped}")
assert escaped == "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"
print("Manual verification of html.escape successful!")
