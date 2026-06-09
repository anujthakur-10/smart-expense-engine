"""
storage.py — Supabase Storage Wrapper
Invoice images/PDFs ko Supabase Storage bucket mein upload karta hai.
Public URL generate karta hai database mein store karne ke liye.
"""

import os
import uuid
from typing import Optional, Tuple
from datetime import datetime
from supabase import create_client, Client
from config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Supabase client singleton
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Supabase client ka singleton instance"""
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY,
        )
    return _supabase_client


class StorageService:
    """
    Supabase Storage operations — upload, download, delete.
    Invoice files cloud mein store hote hain, local filesystem pe nahi.
    """

    def __init__(self):
        self.bucket = settings.STORAGE_BUCKET
        self.client = get_supabase_client()

    async def upload_file(
        self,
        file_bytes: bytes,
        original_filename: str,
        user_id: str,
        content_type: str = "image/jpeg",
    ) -> Tuple[str, str]:
        """
        File ko Supabase Storage mein upload karta hai.

        Args:
            file_bytes: File ka raw bytes data
            original_filename: Original file name
            user_id: User ID (folder structure ke liye)
            content_type: MIME type

        Returns:
            Tuple of (file_url, storage_path)
        """
        try:
            # Unique filename generate karo (collision avoid karne ke liye)
            ext = os.path.splitext(original_filename)[1].lower()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_name = f"{timestamp}_{uuid.uuid4().hex[:8]}{ext}"

            # User-specific folder structure
            storage_path = f"{user_id}/{unique_name}"

            # Upload to Supabase Storage
            self.client.storage.from_(self.bucket).upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "false"},
            )

            # Public URL generate karo
            file_url = self.client.storage.from_(self.bucket).get_public_url(storage_path)

            logger.info(f"☁️ File uploaded: {storage_path}")
            return file_url, storage_path

        except Exception as e:
            logger.error(f"❌ Storage upload failed: {e}")
            # Fallback: Return a placeholder URL
            return f"/uploads/{original_filename}", original_filename

    async def delete_file(self, storage_path: str) -> bool:
        """Storage se file delete karta hai"""
        try:
            self.client.storage.from_(self.bucket).remove([storage_path])
            logger.info(f"🗑️ File deleted: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Delete failed: {e}")
            return False

    async def get_file_url(self, storage_path: str) -> str:
        """File ka public URL return karta hai"""
        return self.client.storage.from_(self.bucket).get_public_url(storage_path)
