"""
Unit tests for app.utils.crypto — Fernet-based credential encryption.
"""
from cryptography.fernet import Fernet

from app.utils.crypto import decrypt_config, encrypt_config, safe_config_for_response

TEST_KEY = Fernet.generate_key().decode()
TEST_CREDS = {"access_token": "tok_abc123", "api_key": "key_xyz_secret"}


# ── Round-trip ────────────────────────────────────────────────────────────────

def test_round_trip(monkeypatch):
    """encrypt_config → decrypt_config returns the original dict."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)
    encrypted = encrypt_config(TEST_CREDS)
    assert "_enc" in encrypted
    decrypted = decrypt_config(encrypted)
    assert decrypted == TEST_CREDS


def test_different_keys_cannot_decrypt(monkeypatch):
    """Data encrypted with key A cannot be decrypted with key B."""
    key_a = Fernet.generate_key().decode()
    key_b = Fernet.generate_key().decode()

    monkeypatch.setattr("app.config.settings.credentials_key", key_a)
    encrypted = encrypt_config(TEST_CREDS)

    monkeypatch.setattr("app.config.settings.credentials_key", key_b)
    result = decrypt_config(encrypted)
    # Wrong key → returns empty dict (safe fallback, not an exception)
    assert result == {}


def test_encrypted_blob_is_opaque(monkeypatch):
    """Raw credential values must not appear as plaintext in the stored blob."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)
    encrypted = encrypt_config(TEST_CREDS)
    blob = str(encrypted)
    assert "tok_abc123" not in blob
    assert "key_xyz_secret" not in blob


def test_each_encryption_produces_different_ciphertext(monkeypatch):
    """Fernet is probabilistic — the same plaintext produces different tokens each time."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)
    enc1 = encrypt_config(TEST_CREDS)
    enc2 = encrypt_config(TEST_CREDS)
    assert enc1["_enc"] != enc2["_enc"]
    # But both decrypt to the same value
    assert decrypt_config(enc1) == decrypt_config(enc2) == TEST_CREDS


# ── Legacy / no-key fallback ─────────────────────────────────────────────────

def test_legacy_plaintext_passthrough():
    """decrypt_config on a dict without _enc returns it unchanged (backward compat)."""
    legacy = {"access_token": "plain_tok"}
    assert decrypt_config(legacy) == legacy


def test_empty_config_passthrough():
    assert decrypt_config({}) == {}


def test_encrypt_without_key_returns_plaintext(monkeypatch):
    """When CREDENTIALS_KEY is unset, encrypt_config returns the original dict."""
    monkeypatch.setattr("app.config.settings.credentials_key", "")
    result = encrypt_config(TEST_CREDS)
    assert "_enc" not in result
    assert result == TEST_CREDS


def test_decrypt_encrypted_without_key_returns_empty(monkeypatch):
    """An encrypted record + missing CREDENTIALS_KEY → empty dict, not an exception."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)
    encrypted = encrypt_config(TEST_CREDS)

    monkeypatch.setattr("app.config.settings.credentials_key", "")
    result = decrypt_config(encrypted)
    assert result == {}


# ── safe_config_for_response ─────────────────────────────────────────────────

def test_safe_config_masks_values(monkeypatch):
    """safe_config_for_response returns field names with values replaced by ••••."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)
    encrypted = encrypt_config(TEST_CREDS)
    safe = safe_config_for_response(encrypted)
    assert set(safe.keys()) == set(TEST_CREDS.keys())
    for v in safe.values():
        assert v == "••••"


def test_safe_config_on_plaintext_legacy():
    """safe_config_for_response handles unencrypted legacy configs."""
    safe = safe_config_for_response({"token": "secret123", "refresh": "abc"})
    assert set(safe.keys()) == {"token", "refresh"}
    assert "secret123" not in str(safe)
    assert all(v == "••••" for v in safe.values())


def test_safe_config_on_empty():
    assert safe_config_for_response({}) == {}


# ── Integration: connect stores encrypted, list shows only field names ────────

def test_encrypt_connect_decrypt_in_service(monkeypatch):
    """End-to-end: simulate what integrations.py and tools.py do."""
    monkeypatch.setattr("app.config.settings.credentials_key", TEST_KEY)

    # Simulate connect_integration
    raw = {"access_token": "real_token_abc", "webhook_secret": "wh_sec_xyz"}
    stored = encrypt_config(raw)

    # Simulate tools.py reading it back
    recovered = decrypt_config(stored)
    assert recovered["access_token"] == "real_token_abc"
    assert recovered["webhook_secret"] == "wh_sec_xyz"

    # Simulate list_integrations safe view
    response_view = safe_config_for_response(stored)
    assert "real_token_abc" not in str(response_view)
    assert "wh_sec_xyz" not in str(response_view)
