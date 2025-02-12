from typing import List
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import asyncio

import httpx
from langchain_community.document_loaders import WebBaseLoader

from src.services.indexer_service import IndexerService
from src.utils.logger import logger


class WebsiteIndexer:
    """
    A class to handle website indexing with sitemap support.
    """

    def __init__(self, indexer: IndexerService):
        """
        Initialize the WebsiteIndexer.

        Args:
            indexer (IndexerService): The indexer used for document processing.
        """
        self.indexer = indexer
        self.logger = logger

    async def _fetch_sitemap(self, base_url: str) -> List[str]:
        """
        Asynchronously fetch and parse sitemap URLs.

        Args:
            base_url (str): Base URL to fetch the sitemap from.

        Returns:
            List[str]: A list of URLs found in the sitemap.
        """
        sitemap_url = urljoin(base_url, "sitemap.xml")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(sitemap_url)
                response.raise_for_status()

            # Parse the XML content to extract URLs
            root = ET.fromstring(response.content)
            urls = [
                loc.text
                for loc in root.findall(
                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                )
                if loc.text and not loc.text.endswith(".pdf")
            ]

            self.logger.info(f"Found {len(urls)} URLs in sitemap")
            return urls

        except Exception as e:
            self.logger.info(f"No sitemap found for {base_url}: {e}")
            return []

    async def _process_url(self, url: str) -> None:
        """
        Asynchronously process a single URL for indexing.

        Args:
            url (str): The URL to process and index.
        """
        self.logger.info(f"Loading website: {url}")

        try:
            loader = WebBaseLoader(url)
            # Run the blocking loader.load() in a thread to avoid blocking the event loop
            docs = await asyncio.to_thread(loader.load)

            if not self.indexer.text_splitter:
                raise RuntimeError("Text Splitter not initialized.")

            if not self.indexer.vector_store:
                raise RuntimeError("Vector Store not initialized.")

            self.logger.info("Splitting docs into chunks")
            # Run the synchronous text splitting in a thread
            chunks = self.indexer.text_splitter.split_documents(docs)
            self.logger.info(f"Split into {len(chunks)} chunks")

            # Run the blocking vector store addition in a thread
            self.indexer.vector_store.add_documents(chunks)
            self.logger.info(f"Indexing complete for URL: {url}")

        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}")

    async def index_website(self, base_url: str) -> None:
        """
        Asynchronously index a website, using its sitemap if available.

        Args:
            base_url (str): The base URL of the website to index.
        """
        self.logger.info(f"Processing website: {base_url}")

        # Try fetching sitemap URLs; fall back to the base URL if no sitemap is found
        sitemap_urls = await self._fetch_sitemap(base_url)
        urls_to_process = sitemap_urls if sitemap_urls else [base_url]
        urls_to_process = urls_to_process[:20]

        # Process each URL concurrently
        await asyncio.gather(*(self._process_url(url) for url in urls_to_process))


async def load_website(url: str, indexer: IndexerService) -> None:
    """
    Convenience function to asynchronously index a website using WebsiteIndexer.

    Args:
        url (str): The base URL of the website to index.
        indexer (IndexerService): The indexer to use for document processing.
    """
    website_indexer = WebsiteIndexer(indexer)
    await website_indexer.index_website(url)
