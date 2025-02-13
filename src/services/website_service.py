from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin
import asyncio
import xml.etree.ElementTree as ET
from uuid import uuid4

import httpx
from langchain_community.document_loaders import WebBaseLoader
from pydantic import HttpUrl

from src.services.indexer_service import IndexerService
from src.utils.logger import logger


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


class TaskStore:
    """In-memory task storage"""
    def __init__(self):
        self.tasks: Dict[str, TaskInfo] = {}
        self._lock = asyncio.Lock()
    
    async def create_task(self, url: str) -> str:
        async with self._lock:
            # Check if URL is already being processed
            for task in self.tasks.values():
                if task.url == url and task.status.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                    return task.id
            
            task_id = str(uuid4())
            self.tasks[task_id] = TaskInfo(
                id=task_id,
                url=url,
                status=ProcessingStatus(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            return task_id
    
    async def update_task(self, task_id: str, status: ProcessingStatus) -> None:
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status
                self.tasks[task_id].updated_at = datetime.utcnow()
    
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        async with self._lock:
            return self.tasks.get(task_id)


class WebsiteProcessor:
    def __init__(
        self,
        indexer: IndexerService,
        task_store: TaskStore,
        max_concurrent_requests: int = 10,
        connection_timeout: int = 30,
    ):
        self.indexer = indexer
        self.task_store = task_store
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.connection_timeout = connection_timeout

    async def _fetch_sitemap(self, base_url: str) -> List[str]:
        """Fetch and parse sitemap URLs."""
        sitemap_url = urljoin(base_url, "sitemap.xml")
        try:
            async with httpx.AsyncClient(timeout=self.connection_timeout) as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()

            root = ET.fromstring(response.content)
            urls = [
                loc.text
                for loc in root.findall(
                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                )
                if loc.text and not loc.text.endswith(".pdf")
            ]
            return urls

        except Exception as e:
            logger.info(f"No sitemap found for {base_url}: {e}")
            return [base_url]

    async def _process_url(self, url: str, task_id: str) -> bool:
        """Process a single URL with status updates."""
        try:
            async with self.semaphore:
                logger.info(f"Processing URL: {url}")
                
                # Update current URL in status
                task = await self.task_store.get_task(task_id)
                if task:
                    status = task.status
                    status.current_url = url
                    await self.task_store.update_task(task_id, status)

                loader = WebBaseLoader(url)
                docs = await asyncio.to_thread(loader.load)

                if not docs:
                    return False

                chunks = self.indexer.text_splitter.split_documents(docs)
                for chunk in chunks:
                    chunk.metadata["source"] = url

                await self.indexer.vector_store.aadd_documents(chunks)
                return True

        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return False

    async def process_website(self, url: str) -> str:
        """Process website and return task ID for status tracking."""
        task_id = await self.task_store.create_task(url)
        asyncio.create_task(self._process_website_task(url, task_id))
        return task_id

    async def _process_website_task(self, url: str, task_id: str) -> None:
        """Background task for website processing with status updates."""
        try:
            # Initialize status
            urls = await self._fetch_sitemap(url)
            status = ProcessingStatus(
                total_urls=len(urls),
                remaining_urls=urls.copy(),
                status=TaskStatus.IN_PROGRESS
            )
            await self.task_store.update_task(task_id, status)

            # Process URLs
            for url in urls:
                success = await self._process_url(url, task_id)
                
                # Update status
                status.remaining_urls.remove(url)
                if success:
                    status.processed_urls.append(url)
                else:
                    status.failed_urls.append(url)
                
                status.percent_complete = (len(status.processed_urls) / status.total_urls) * 100
                await self.task_store.update_task(task_id, status)

            # Complete status
            status.status = TaskStatus.COMPLETED
            status.current_url = None
            await self.task_store.update_task(task_id, status)

        except Exception as e:
            logger.error(f"Website processing failed: {str(e)}")
            status = ProcessingStatus(
                status=TaskStatus.FAILED,
                error=str(e)
            )
            await self.task_store.update_task(task_id, status)