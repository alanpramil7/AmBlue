from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingStatus:
    total_urls: int = 0
    processed_urls: List[str] = None
    remaining_urls: List[str] = None
    failed_urls: List[str] = None
    current_url: Optional[str] = None
    percent_complete: float = 0
    status: TaskStatus = TaskStatus.PENDING
    error: Optional[str] = None

    def __post_init__(self):
        self.processed_urls = self.processed_urls or []
        self.remaining_urls = self.remaining_urls or []
        self.failed_urls = self.failed_urls or []


@dataclass
class TaskInfo:
    id: str
    url: str
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
