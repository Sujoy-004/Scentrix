import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import settings


class VaultService:
    def __init__(self):
        # Use a master key from environment or a derived one
        master_key = settings.data_encryption_key or "dev_fallback_key_change_in_production"

        # Derive a 32-byte key for Fernet
        salt = b"scentrix_salt"  # In production, use a persistent unique salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.fernet = Fernet(key)

    def encrypt(self, data: str) -> str:
        if not data:
            return ""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        if not encrypted_data:
            return ""
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception:
            # Fallback for unencrypted legacy data or corruption
            return encrypted_data


vault_service = VaultService()
