import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.auth import create_access_token, decode_access_token

def test_auth():
    print("Testing auth module...")
    data = {"sub": "test_user"}
    token = create_access_token(data)
    print(f"Token created: {token[:20]}...")

    decoded = decode_access_token(token)
    print(f"Decoded payload: {decoded}")

    assert decoded["sub"] == "test_user"
    print("Test passed!")

if __name__ == "__main__":
    test_auth()
