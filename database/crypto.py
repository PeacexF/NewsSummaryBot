# Гыгы крипта

# This module does the encryption of API keys

import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

_KEY = os.getenv("ENCRYPTION_KEY")
if not _KEY:
    raise ValueError("ENCRYPTION_KEY is not set in .env file")

_fernet = Fernet(_KEY.encode())


def encrypt_key(plain_text: str) -> str:
    # classic str to str: bytes encode -> encrypt -> decode back into str -> store
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.strip().encode()).decode()


def decrypt_key(cipher_text: str) -> str:
    # same but the other way around
    if not cipher_text:
        return ""
    try:
        return _fernet.decrypt(cipher_text.encode()).decode()
    except Exception:
        return ""