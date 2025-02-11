import asyncio
import logging
from typing import List
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import aiohttp
from langchain_community.document_loaders import WebBaseLoader

from src.services.indexer_service import IndexerService
from src.utils.logger import logger


class WebsiteIndexer:
    """A class to handle website indexing with sitemap support and concurrent processing."""

    def __init__(self, indexer: IndexerService):
        """Initialize the WebsiteIndexer."""
        self.indexer = indexer
        self.logger = logger
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

    async def _fetch_sitemap(self, base_url: str) -> List[str]:
        """
        Fetch and parse sitemap URLs asynchronously.

        Args:
            base_url (str): Base URL to fetch sitemap from.

        Returns:
            List[str]: List of URLs from the sitemap.
        """
        sitemap_url = urljoin(base_url, "sitemap.xml")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(sitemap_url, timeout=10) as response:
                    if response.status != 200:
                        self.logger.info(f"No sitemap found at {sitemap_url}")
                        return []

                    content = await response.text()
                    root = ET.fromstring(content)
                    urls = [
                        loc.text
                        for loc in root.findall(
                            ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                        )
                        if loc.text and not loc.text.endswith(".pdf")
                    ]

                    self.logger.info(f"Found {len(urls)} urls in sitemap")
                    return urls

            except Exception as e:
                self.logger.info(f"Error fetching sitemap for {base_url}: {e}")
                return []

    async def _process_url(self, url: str) -> None:
        """
        Process a single URL for indexing with rate limiting.

        Args:
            url (str): URL to process and index.
        """
        async with self.semaphore:  # Limit concurrent processing
            self.logger.info(f"Processing URL: {url}")
            try:
                # Run CPU-intensive operations in a thread pool
                loader = WebBaseLoader(url)
                docs = await asyncio.to_thread(loader.load)

                if not self.indexer.text_splitter:
                    raise RuntimeError("Text Splitter not initialized.")

                if not self.indexer.vector_store:
                    raise RuntimeError("Vector Store not initialized.")

                # Split documents into chunks
                chunks = await asyncio.to_thread(
                    self.indexer.text_splitter.split_documents, docs
                )
                self.logger.info(f"Split into {len(chunks)} chunks")

                # Add documents to vector store
                await asyncio.to_thread(self.indexer.vector_store.add_documents, chunks)
                self.logger.info(f"Indexed URL: {url}")

            except Exception as e:
                self.logger.error(f"Error processing URL {url}: {e}")

    async def index_website(self, base_url: str) -> None:
        """
        Index a website concurrently, using sitemap if available.

        Args:
            base_url (str): Base URL of the website to index.
        """
        self.logger.info(f"Starting website indexing: {base_url}")

        # Fetch sitemap URLs or use base URL
        urls = await self._fetch_sitemap(base_url) or [base_url]

        urls = urls[:20]
        # Process URLs concurrently with rate limiting
        tasks = [self._process_url(url) for url in urls]
        await asyncio.gather(*tasks)

        self.logger.info(f"Completed indexing website: {base_url}")
