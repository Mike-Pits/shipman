from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImapSettings(Base):
    """Singleton row (id=1). FR-16: the operator can choose the mailbox folder
    at will — it's a runtime setting, not fixed by the SHIPMAN_MAILBOX_FOLDER
    env var, which only supplies the initial default."""

    __tablename__ = "imap_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder: Mapped[str] = mapped_column(String, nullable=False)
