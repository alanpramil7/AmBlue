import asyncio
import json
import os
from asyncio import Semaphore
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import aiohttp
import cachetools
from aiohttp import ClientSession, TCPConnector
from langchain_core.documents import Document

from src.services.indexer_service import IndexerService
from src.utils.logger import logger


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
    processed_pages: list[str]
    remaining_pages: list[str]
    failed_pages: list[str]
    current_page: str | None
    percent_complete: float
    error: str | None


@dataclass
class Task:
    """Represents a processing task."""
    id: str
    status: TaskInfo


class TaskStore:
    """Store for tracking task status and progress."""
    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self._lock = asyncio.Lock()

    async def create_task(self, task_id: str, total_pages: int) -> Task:
        """Create a new task with initial status."""
        async with self._lock:
            task = Task(
                id=task_id,
                status=TaskInfo(
                    status=TaskStatus.PENDING,
                    total_pages=total_pages,
                    processed_pages=[],
                    remaining_pages=[],
                    failed_pages=[],
                    current_page=None,
                    percent_complete=0.0,
                    error=None,
                ),
            )
            self.tasks[task_id] = task
            return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        async with self._lock:
            return self.tasks.get(task_id)

    async def update_task(self, task_id: str, status: TaskInfo) -> None:
        """Update a task's status."""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].status = status

    async def get_task_by_wiki(self, organization: str, project: str, wiki_identifier: str) -> Optional[str]:
        """Get task ID by wiki details if it is already being processed."""
        task_id = f"{organization}_{project}_{wiki_identifier}"
        async with self._lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                    return task_id
            return None


@dataclass
class WikiPage:
    """Represents a single wiki page with its metadata and content."""

    page_path: str
    content: str
    remote_url: Optional[str] = None


class WikiClientError(Exception):
    """Custom exception for Wiki Client related errors."""

    pass


def _make_cache_key(params: Dict[str, Any], method: str = "GET") -> str:
    """Create a hashable cache key from request parameters."""
    sorted_params = json.dumps(params, sort_keys=True)
    return f"{method}:{sorted_params}"


def _prepare_params(params: Dict[str, Any]) -> Dict[str, str]:
    """
    Convert parameter values to strings suitable for URL query parameters.

    Args:
        params (Dict[str, Any]): Original parameters

    Returns:
        Dict[str, str]: Parameters with values converted to strings
    """
    prepared = {}
    for key, value in params.items():
        if isinstance(value, bool):
            prepared[key] = str(value).lower()
        elif value is not None:
            prepared[key] = str(value)
    return prepared


class WikiClient:
    """
    Concurrent-capable client for interacting with Azure DevOps Wiki REST API.
    """

    def __init__(
        self,
        organization: str,
        project: str,
        wiki_identifier: str,
        personal_access_token: str,
        max_concurrent_requests: int = 10,
        connection_timeout: int = 30,
    ):
        """Initialize the Wiki Client with Azure DevOps credentials and connection settings."""
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis/wiki/wikis/{wiki_identifier}/pages"
        self.auth = aiohttp.BasicAuth("", personal_access_token)
        self.api_version = "7.1"
        self.semaphore = Semaphore(max_concurrent_requests)
        self.session = None
        self.connection_timeout = connection_timeout
        self.processing_pages: Set[str] = set()
        self.cache = cachetools.TTLCache(maxsize=100, ttl=3600)  # 1-hour cache

    async def __aenter__(self):
        """Initialize the aiohttp session when entering context."""
        connector = TCPConnector(limit=50)  # Connection pool size
        timeout = aiohttp.ClientTimeout(total=self.connection_timeout)
        self.session = ClientSession(
            connector=connector, timeout=timeout, auth=self.auth
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the aiohttp session when exiting context."""
        if self.session:
            await self.session.close()

    async def _make_api_request(
        self, params: Dict[str, Any], method: str = "GET"
    ) -> Optional[Dict[str, Any]]:
        """Makes API requests with connection pooling and rate limiting."""
        if not self.session:
            raise WikiClientError("Client session not initialized")

        # Create cache key from original params
        cache_key = _make_cache_key(params, method)

        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Prepare parameters for the request
        request_params = _prepare_params({**params, "api-version": self.api_version})

        async with self.semaphore:  # Control concurrent requests
            try:
                async with self.session.request(
                    method, self.base_url, params=request_params
                ) as response:
                    if response.status == 429:  # Rate limit hit
                        retry_after = int(response.headers.get("Retry-After", 5))
                        logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        return await self._make_api_request(params, method)

                    response.raise_for_status()
                    result = await response.json()

                    # Cache the result
                    self.cache[cache_key] = result
                    return result

            except aiohttp.ClientError as e:
                logger.error(f"API Request failed: {str(e)}")
                return None

    async def _get_page_content(self, page_path: str) -> str:
        """Retrieves the content for a specific wiki page with caching."""
        # Prevent duplicate processing
        if page_path in self.processing_pages:
            while page_path in self.processing_pages:
                await asyncio.sleep(0.1)
            return self.cache.get(f"content_{page_path}", "")

        self.processing_pages.add(page_path)
        try:
            params = {"path": page_path, "includeContent": True}
            result = await self._make_api_request(params)

            if result:
                content = result.get("content", "")
                self.cache[f"content_{page_path}"] = content
                return content
            return ""
        finally:
            self.processing_pages.remove(page_path)

    async def _get_wiki_tree(self) -> Optional[Dict[str, Any]]:
        """Retrieves the complete wiki page tree with caching."""
        params = {"path": "/", "recursionLevel": "full", "includeContent": True}
        return await self._make_api_request(params)

    async def _flatten_pages(self, page: Dict[str, Any]) -> List[WikiPage]:
        """Recursively flattens the wiki page tree with concurrent processing."""
        pages = []
        page_path = page.get("path", "/")
        content = page.get("content")
        remote_url = page.get("remoteUrl")

        if not content:
            content = await self._get_page_content(page_path)

        if content:
            pages.append(
                WikiPage(page_path=page_path, content=content, remote_url=remote_url)
            )

        # Process subpages concurrently
        subpages = page.get("subPages", [])
        tasks = [self._flatten_pages(subpage) for subpage in subpages]
        results = await asyncio.gather(*tasks)

        for result in results:
            pages.extend(result)

        return pages


class WikiService:
    """Service for processing wiki pages with task tracking."""

    def __init__(self, indexer: IndexerService, task_store: TaskStore):
        self.indexer = indexer
        self.task_store = task_store

    async def _process_wiki_pages(
        self,
        task_id: str,
        organization: str,
        project: str,
        wiki_identifier: str,
        max_concurrent_requests: int = 10,
    ) -> None:
        """Internal method to process wiki pages and update task status."""
        try:
            pages = await fetch_wiki_pages(
                organization,
                project,
                wiki_identifier,
                max_concurrent_requests,
            )

            if not pages:
                logger.info("No Pages found.")
                await self.task_store.update_task(
                    task_id,
                    TaskInfo(
                        status=TaskStatus.COMPLETED,
                        total_pages=0,
                        processed_pages=[],
                        remaining_pages=[],
                        failed_pages=[],
                        current_page=None,
                        percent_complete=100.0,
                        error=None,
                    ),
                )
                return

            if not self.indexer.vector_store:
                logger.error("Vector store not initialized")
                raise Exception("Vector store not initialized")

            # Initialize status
            total_pages = len(pages)
            remaining_pages = [page.page_path for page in pages]

            # Update initial status
            await self.task_store.update_task(
                task_id,
                TaskInfo(
                    status=TaskStatus.IN_PROGRESS,
                    total_pages=total_pages,
                    processed_pages=[],
                    remaining_pages=remaining_pages,
                    failed_pages=[],
                    current_page=remaining_pages[0] if remaining_pages else None,
                    percent_complete=0.0,
                    error=None,
                ),
            )

            # Process pages in chunks
            chunk_size = 10
            processed_pages = []
            failed_pages = []

            for i in range(0, len(pages), chunk_size):
                chunk = pages[i : i + chunk_size]
                docs = []

                for page in chunk:
                    try:
                        if not page.content.strip():
                            continue

                        lines = [line.strip() for line in page.content.split("\n")]
                        non_empty_lines = [line for line in lines if line]

                        if not non_empty_lines:
                            continue

                        if len(non_empty_lines) == 1:
                            line = non_empty_lines[0]
                            if line.startswith("#") or line.startswith("!["): 
                                continue

                        doc = Document(
                            page_content=page.content,
                            metadata={
                                "source": f"wiki_{page.page_path}",
                                "organization": organization,
                                "project": project,
                            },
                        )
                        docs.append(doc)
                        processed_pages.append(page.page_path)
                    except Exception as e:
                        logger.error(f"Error processing page {page.page_path}: {str(e)}")
                        failed_pages.append(page.page_path)

                if docs:
                    await self.indexer.vector_store.aadd_documents(docs)
                    logger.info(f"Processed chunk of {len(docs)} documents")

                # Update task status
                remaining_pages = [p for p in remaining_pages if p not in processed_pages and p not in failed_pages]
                percent_complete = (len(processed_pages) + len(failed_pages)) / total_pages * 100

                await self.task_store.update_task(
                    task_id,
                    TaskInfo(
                        status=TaskStatus.IN_PROGRESS,
                        total_pages=total_pages,
                        processed_pages=processed_pages,
                        remaining_pages=remaining_pages,
                        failed_pages=failed_pages,
                        current_page=remaining_pages[0] if remaining_pages else None,
                        percent_complete=percent_complete,
                        error=None,
                    ),
                )

            # Update final status
            final_status = TaskStatus.COMPLETED if not failed_pages else TaskStatus.FAILED
            await self.task_store.update_task(
                task_id,
                TaskInfo(
                    status=final_status,
                    total_pages=total_pages,
                    processed_pages=processed_pages,
                    remaining_pages=[],
                    failed_pages=failed_pages,
                    current_page=None,
                    percent_complete=100.0,
                    error=f"Failed to process {len(failed_pages)} pages" if failed_pages else None,
                ),
            )

        except Exception as e:
            logger.error(f"Error processing wiki: {str(e)}")
            await self.task_store.update_task(
                task_id,
                TaskInfo(
                    status=TaskStatus.FAILED,
                    total_pages=0,
                    processed_pages=[],
                    remaining_pages=[],
                    failed_pages=[],
                    current_page=None,
                    percent_complete=0.0,
                    error=str(e),
                ),
            )

    async def process_wiki(
        self,
        organization: str,
        project: str,
        wiki_identifier: str,
        max_concurrent_requests: int = 10,
    ) -> str:
        """Start wiki processing in the background and return task ID."""
        task_id = f"{organization}_{project}_{wiki_identifier}"

        # Create task with initial status
        await self.task_store.create_task(task_id, 0)

        # Start processing in background
        asyncio.create_task(
            self._process_wiki_pages(
                task_id,
                organization,
                project,
                wiki_identifier,
                max_concurrent_requests,
            )
        )

        return task_id


async def fetch_wiki_pages(
    organization: str,
    project: str,
    wiki_identifier: str,
    max_concurrent_requests: int = 10,
) -> Optional[List[WikiPage]]:
    """Fetch all wiki pages concurrently with proper resource management."""
    access_token = os.getenv("WIKI_ACCESS_TOKEN")
    if not access_token:
        logger.error("WIKI_ACCESS_TOKEN environment variable not set")
        return None

    try:
        async with WikiClient(
            organization,
            project,
            wiki_identifier,
            access_token,
            max_concurrent_requests,
        ) as client:
            wiki_tree = await client._get_wiki_tree()
            if wiki_tree:
                return await client._flatten_pages(wiki_tree)

        return None

    except Exception as e:
        logger.error(f"Wiki page retrieval failed: {str(e)}")
        logger.exception("Detailed error trace:")
        return None
