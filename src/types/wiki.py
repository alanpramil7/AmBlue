from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class TaskStatus(Enum):
    """Enum for task processing status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskInfo:
    """Information about a task's status and progress."""

    status: TaskStatus
    total_pages: int
    processed_pages: List[str]
    remaining_pages: List[str]
    failed_pages: List[str]
    current_page: Optional[str]
    percent_complete: float
    error: Optional[str]


@dataclass
class Task:
    """Represents a processing task."""

    id: str
    status: TaskInfo
