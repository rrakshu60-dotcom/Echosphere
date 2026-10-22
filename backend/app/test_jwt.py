import pytest

from app.core.jwt_handler import create_access_token, verify_access_token


def test_token_round_trips_its_claims():
    token = create_access_token({"sub": "teacher@college.edu", "role": "Teacher"})
    payload = verify_access_token(token)
    assert payload["sub"] == "teacher@college.edu"
    assert payload["role"] == "Teacher"
    assert "exp" in payload


def test_tampered_token_is_rejected():
    token = create_access_token({"sub": "teacher@college.edu", "role": "Teacher"})
    head, body, sig = token.split(".")
    tampered = ".".join([head, body, ("A" if sig[0] != "A" else "B") + sig[1:]])
    with pytest.raises(ValueError):
        verify_access_token(tampered)
