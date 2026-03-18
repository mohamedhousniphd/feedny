from app.auth import get_password_hash, verify_password

def test_get_password_hash_returns_hashed_string():
    """Test that get_password_hash hashes the password and does not return plaintext."""
    password = "super_secret_password"
    hashed = get_password_hash(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert len(hashed) > 0

def test_get_password_hash_different_passwords():
    """Test that different passwords result in different hashes."""
    pwd1 = "password123"
    pwd2 = "password456"
    assert get_password_hash(pwd1) != get_password_hash(pwd2)

def test_verify_password_success():
    """Test that a valid password and its hash return True."""
    password = "another_secret_password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True

def test_verify_password_failure():
    """Test that an invalid password returns False."""
    password = "correct_password"
    wrong_password = "wrong_password"
    hashed = get_password_hash(password)
    assert verify_password(wrong_password, hashed) is False

def test_get_password_hash_empty_string():
    """Test edge case of hashing an empty string."""
    password = ""
    hashed = get_password_hash(password)
    assert hashed != password
    assert isinstance(hashed, str)
    assert verify_password(password, hashed) is True
