from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PolicyDocument:
    """Represents a climate policy document extracted from the web."""
    title: str
    source_url: str
    file_path: str
    content: str
    download_date: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    file_type: str = "pdf"
    embedding: Optional[list[float]] = None

    def to_metadata(self) -> dict:
        """Returns the metadata dictionary for the database."""
        return {
            "title": self.title,
            "source_url": self.source_url,
            "file_path": self.file_path,
            "download_date": self.download_date,
            "file_type": self.file_type
        }
