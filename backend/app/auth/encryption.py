from cryptography.fernet import Fernet

from app.config import settings


class DataVault:
    """AES-256 Fernet-based encryption for PII fields."""

    def __init__(self):
        self.fernet = Fernet(settings.data_encryption_key.encode())

    def encrypt(self, data: str) -> str:
        """Encrypt string data for DB storage."""
        if not data:
            return data
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data from DB storage.
        
        Raises:
            ValueError: If decryption fails.
        """
        if not encrypted_data:
            return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as exc:
            raise ValueError("Decryption failed: Data is corrupt or key is invalid") from exc


vault = DataVault()
