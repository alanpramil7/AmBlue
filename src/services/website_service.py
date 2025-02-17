import asyncio
import hashlib
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import urljoin
from uuid import uuid4

import httpx
from langchain_community.document_loaders import WebBaseLoader

from src.services.database_service import DatabaseService
from src.services.indexer_service import IndexerService
from src.types.website import ProcessingStatus, TaskStatus
from src.utils.logger import logger


class WebsiteService:
    def __init__(
        self,
        indexer: IndexerService,
        database: DatabaseService,
        max_concurrent_requests: int = 10,
        connection_timeout: int = 30,
    ):
        self.indexer = indexer
        self.database = database
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.connection_timeout = connection_timeout
        self.processed_hashes = set()

    def _get_content_hash(self, content: str) -> str:
        """Generate a unique hash for content and URL combination."""
        return hashlib.md5(f"{content}".encode()).hexdigest()

    async def _fetch_sitemap(self, base_url: str) -> List[str]:
        """Fetch and parse sitemap URLs."""
        logger.info(f"Fetching sitemap for {base_url}")
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
            logger.info(f"Urls found {len(urls)}")
            return urls

        except Exception as e:
            logger.info(f"No sitemap found for {base_url}: {e}")
            return [base_url]

    async def _process_url(self, url: str, task_id: str) -> bool:
        """Process a single URL with status updates and deduplication."""
        try:
            async with self.semaphore:
                logger.info(f"Processing URL: {url}")

                # Update current URL in status
                task = self.database.get_task(task_id)
                if task:
                    status = ProcessingStatus(
                        total_urls=task["status"]["total_urls"],
                        processed_urls=task["status"]["processed_urls"],
                        remaining_urls=task["status"]["remaining_urls"],
                        failed_urls=task["status"]["failed_urls"],
                        current_url=url,
                        percent_complete=task["status"]["percent_complete"],
                        status=task["status"]["status"],
                        error=task["status"]["error"],
                    )
                    self.database.update_task_status(task_id, status)

                loader = WebBaseLoader(url)
                docs = await asyncio.to_thread(loader.load)

                if not docs:
                    return False

                chunks = self.indexer.text_splitter.split_documents(docs)
                unique_chunks = []

                for chunk in chunks:
                    chunk.metadata["source"] = url
                    content_hash = self._get_content_hash(chunk.page_content)

                    if content_hash not in self.processed_hashes:
                        self.processed_hashes.add(content_hash)
                        chunk.metadata["content_hash"] = content_hash
                        unique_chunks.append(chunk)

                if unique_chunks:
                    await self.indexer.vector_store.aadd_documents(unique_chunks)
                    logger.info(f"Added {len(unique_chunks)} for {url}")
                return True

        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return False

    async def process_website(self, url: str) -> str:
        """Process website and return task ID for status tracking."""
        task_id = str(uuid4())
        self.database.create_processing_task(task_id, url)
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
                status=TaskStatus.IN_PROGRESS,
            )
            self.database.update_task_status(task_id, status)

            # Process URLs
            for url in urls:
                success = await self._process_url(url, task_id)

                # Update status
                status.remaining_urls.remove(url)
                if success:
                    status.processed_urls.append(url)
                else:
                    status.failed_urls.append(url)

                status.percent_complete = (
                    len(status.processed_urls) / status.total_urls
                ) * 100
                self.database.update_task_status(task_id, status)

            # Complete status
            status.status = TaskStatus.COMPLETED
            status.current_url = None
            self.database.update_task_status(task_id, status)

        except Exception as e:
            logger.error(f"Website processing failed: {str(e)}")
            status = ProcessingStatus(status=TaskStatus.FAILED, error=str(e))
            self.database.update_task_status(task_id, status)
