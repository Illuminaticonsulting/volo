"""
VOLO — Credential Encryption Utilities
Fernet-based symmetric encryption for integration credentials stored in the DB.
"""

import json
import logging
from typing import Any

logger = logging.getLogger("volo.crypto")

# Sentinel key stored in the JSON blob to indicate an encrypted payload
_ENC_FIELD = "_enc"


def _fernet():
    """Return a Fernet instance using the configured credentials_key, or None if unset."""
    from app.config import settings
    key = settings.credentials_key
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception:
        logger.warning("Invalid CREDENTIALS_KEY — cannot initialize encryption", exc_info=True)
        return None


def encrypt_config(config: dict) -> dict:
    """
    Encrypt a credentials dict.
    Returns {"_enc": "<token>"} if encryption is available,
    otherwise returns the original dict unchanged (with a warning).
    """
    f = _fernet()
    if f is None:
        logger.warning(
            "CREDENTIALS_KEY not set — storing integration credentials in plaintext. "
            "Set CREDENTIALS_KEY in .env for production deployments."
        )
        return config
    try:
        token = f.encrypt(json.dumps(config).encode()).decode()
        return {_ENC_FIELD: token}
    except Exception:
        logger.exception("Encryption error for integration data")
        return config


def decrypt_config(config: dict) -> dict:
    """
    Decrypt a credentials dict previously encrypted with encrypt_config.
    If the dict has no _enc field (plaintext legacy record), returns it unchanged.
    """
    if not config or _ENC_FIELD not in config:
        return config  # plaintext (legacy) or empty
    f = _fernet()
    if f is None:
        logger.error(
            "CREDENTIALS_KEY not set but encrypted credentials found in DB — "
            "cannot decrypt. Set CREDENTIALS_KEY to the original key."
        )
        return {}
    try:
        raw = f.decrypt(config[_ENC_FIELD].encode())
        return json.loads(raw)
    except Exception:
        logger.exception("Decryption error for integration data")
        return {}


def safe_config_for_response(config: dict) -> dict[str, Any]:
    """
    Return a sanitized view of a config dict safe to include in API responses.
    Decrypts if needed, then strips all values to just the key names so that
    credentials are never echoed back to the client.
    """
    decrypted = decrypt_config(config)
    return {k: "••••" for k in decrypted}
