from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_reset_password_xss():
    # Attempt to inject a script tag via the token parameter
    xss_payload = "<script>alert('XSS')</script>"
    response = client.get(f"/reset-password?token={xss_payload}")

    assert response.status_code == 200

    # Check that the payload was escaped
    assert "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in response.text
    assert "<script>alert('XSS')</script>" not in response.text
    print("XSS prevention in reset-password verified!")

if __name__ == "__main__":
    test_reset_password_xss()
