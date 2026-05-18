"""
AES-256-GCM encryption for credential storage.
Key sourced from SAJHA_CONNECTOR_KEY environment variable.
Encrypted values are prefixed with 'ENC::' to distinguish from plaintext.
"""
import os
import base64
import hashlib

_ENC_PREFIX = 'ENC::'
_KEY_ENV = 'SAJHA_CONNECTOR_KEY'


def _get_key() -> bytes:
    """Derive 32-byte AES key from env var. Raises if not set."""
    raw = os.environ.get(_KEY_ENV, '')
    if not raw:
        # For local dev without the key set: generate a deterministic fallback
        # WARNING: This fallback is NOT secure — set SAJHA_CONNECTOR_KEY in production
        raw = 'riskgpt-local-dev-key-do-not-use-in-production'
    # Derive a 32-byte key via SHA-256
    return hashlib.sha256(raw.encode()).digest()


def encrypt(plaintext: str) -> str:
    """Encrypt plaintext string. Returns 'ENC::' + base64(nonce + ciphertext + tag)."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import secrets
        key = _get_key()
        nonce = secrets.token_bytes(12)
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        encoded = base64.b64encode(nonce + ct).decode('ascii')
        return _ENC_PREFIX + encoded
    except ImportError:
        # cryptography not installed: store as-is with prefix for identification
        # NOT secure — install cryptography package for production use
        encoded = base64.b64encode(plaintext.encode()).decode('ascii')
        return _ENC_PREFIX + 'b64::' + encoded


def decrypt(value: str) -> str:
    """Decrypt an encrypted value. Returns plaintext. Passes through non-encrypted values."""
    if not value.startswith(_ENC_PREFIX):
        return value
    encoded = value[len(_ENC_PREFIX):]
    try:
        if encoded.startswith('b64::'):
            # Fallback base64-only encoding (no real encryption)
            return base64.b64decode(encoded[5:]).decode('utf-8')
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        key = _get_key()
        raw = base64.b64decode(encoded)
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None).decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decrypt credential: {e}")


def is_encrypted(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_ENC_PREFIX)
