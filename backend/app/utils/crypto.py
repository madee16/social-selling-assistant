import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import Text, TypeDecorator

from app.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    material = settings.token_encryption_key or settings.secret_key
    key = base64.urlsafe_b64encode(hashlib.sha256(material.encode("utf-8")).digest())
    return Fernet(key)


class EncryptedString(TypeDecorator):
    """Transparently encrypt/decrypt a string column with Fernet.

    Values written through the ORM are stored encrypted; reads decrypt them
    back to plaintext. Legacy plaintext rows (stored before encryption was
    enabled) are returned unchanged so existing data keeps working until it
    is rewritten.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return _fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError):
            return value
