import asyncio
import xml.etree.ElementTree as ET
from asyncio import Semaphore
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urljoin

import cachetools
import httpx
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document

from src.services.indexer_service import IndexerService
from src.utils.logger import logger


@dataclass
class WebPage:
    """Represents a single web page with its content."""

    url: str
    content: Optional[str] = None


class WebsiteClientError(Exception):
    """Custom exception for Website Client related errors."""

    pass


class WebsiteClient:
    """
    Concurrent-capable client for processing websites.
    """

    def __init__(
        self,
        base_url: str,
        indexer: IndexerService,
        max_concurrent_requests: int = 10,
        connection_timeout: int = 30,
    ):
        """Initialize the Website Client with processing settings."""
        self.base_url = base_url
        self.indexer = indexer
        self.semaphore = Semaphore(max_concurrent_requests)
        self.connection_timeout = connection_timeout
        self.processing_urls: Set[str] = set()
        self.cache = cachetools.TTLCache(maxsize=100, ttl=3600)  # 1-hour cache
        self.processed_urls = []
        self.processed_pages = 0

    async def _fetch_sitemap(self) -> List[str]:
        """Fetch and parse sitemap URLs."""
        sitemap_url = urljoin(self.base_url, "sitemap.xml")
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

            logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls

        except Exception as e:
            logger.info(f"No sitemap found for {self.base_url}: {e}")
            return [self.base_url]

    async def _process_url(self, url: str) -> Optional[Document]:
        """Process a single URL with rate limiting and caching."""
        if url in self.processing_urls:
            return None

        self.processing_urls.add(url)
        try:
            async with self.semaphore:
                if url in self.cache:
                    return self.cache[url]

                logger.info(f"Processing URL: {url}")

                try:
                    loader = WebBaseLoader(url)
                    docs = await asyncio.to_thread(loader.load)

                    if not docs:
                        return None

                    chunks = self.indexer.text_splitter.split_documents(docs)

                    for chunk in chunks:
                        chunk.metadata["source"] = url

                    await self.indexer.vector_store.aadd_documents(chunks)
                    self.processed_pages += len(chunks)
                    self.processed_urls.append(url)

                    return docs[0]

                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    return None

        finally:
            self.processing_urls.remove(url)

    async def process_website(self) -> dict:
        """Process entire website concurrently."""
        urls = await self._fetch_sitemap()

        # Process URLs concurrently
        tasks = [self._process_url(url) for url in urls]
        await asyncio.gather(*tasks)

        return {
            "processed_pages": self.processed_pages,
            "processed_urls": self.processed_urls,
        }


async def process_website_pages(
    url: str,
    indexer: IndexerService,
    max_concurrent_requests: int = 10,
) -> Optional[dict]:
    """
    Process website pages concurrently with proper resource management.
    """
    try:
        client = WebsiteClient(
            url,
            indexer,
            max_concurrent_requests,
        )
        return await client.process_website()

    except Exception as e:
        logger.error(f"Website processing failed: {str(e)}")
        logger.exception("Detailed error trace:")
        return None
