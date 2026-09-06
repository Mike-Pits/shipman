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


class ImapFolderVesselMapping(Base):
    """Folder↔vessel registry safeguard: remembers which vessel each IMAP folder
    was last (confirmed to be) polled for, so that polling a known folder under a
    different vessel is caught rather than silently misattributing every message
    in it — this is the accident the registry exists to prevent, not a
    hypothetical one (see ADR-0005)."""

    __tablename__ = "imap_folder_vessel_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    folder: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    vessel_id: Mapped[int] = mapped_column(Integer, nullable=False)
