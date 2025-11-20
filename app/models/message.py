from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
import uuid

from app.db.base import Base
from app.core.encryption import EncryptionService
from app.core.logging import get_logger

logger = get_logger(__name__)


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    _encrypted_content = Column("content", Text, nullable=False)  # Stored encrypted
    encryption_version = Column(String, default="v1", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("Session", back_populates="messages")

    @hybrid_property
    def content(self) -> str:
        """
        Decrypt and return the message content.
        This property is transparent to the application - it automatically
        decrypts when accessed.
        """
        try:
            return EncryptionService.decrypt(
                self._encrypted_content,
                self.encryption_version
            )
        except Exception as e:
            logger.error(f"Failed to decrypt message {self.id}: {e}")
            # In production, you might want to handle this differently
            # For now, return a placeholder
            return "[Decryption failed]"

    @content.setter
    def content(self, plaintext: str):
        """
        Encrypt and store the message content.
        This property is transparent to the application - it automatically
        encrypts when set.
        """
        encrypted_text, version = EncryptionService.encrypt(plaintext)
        self._encrypted_content = encrypted_text
        self.encryption_version = version
