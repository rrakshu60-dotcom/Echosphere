from app.core.password import hash_password, verify_password


def test_hash_verifies_only_the_right_password():
    hashed = hash_password("Teacher@123")
    assert hashed != "Teacher@123"
    assert verify_password("Teacher@123", hashed)
    assert not verify_password("Teacher@321", hashed)


def test_malformed_hash_is_rejected_not_raised():
    assert verify_password("Teacher@123", "not-a-bcrypt-hash") is False
