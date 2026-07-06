from app.core.security import hash_password, verify_password


def test_verify_password_accepts_correct_password():
    password_hash = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", password_hash) is True


def test_verify_password_rejects_wrong_password():
    password_hash = hash_password("correct-horse-battery-staple")
    assert verify_password("wrong-password", password_hash) is False


def test_hash_password_is_not_the_plaintext():
    password_hash = hash_password("correct-horse-battery-staple")
    assert password_hash != "correct-horse-battery-staple"


def test_hash_password_produces_different_hashes_for_same_password():
    # Argon2 includes a random salt per hash - two hashes of the same
    # password must differ, otherwise the salt isn't actually random.
    first = hash_password("same-password")
    second = hash_password("same-password")
    assert first != second
    assert verify_password("same-password", first) is True
    assert verify_password("same-password", second) is True
