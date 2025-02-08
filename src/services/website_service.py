import logging
from typing import List
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests
from langchain_community.document_loaders import WebBaseLoader

from src.services.indexer_service import IndexerService
from src.utils.logger import get_logger

logger = get_logger("WebsiteService", logging.INFO)


class WebsiteIndexer:
    """
    A class to handle website indexing with sitemap support.

    Attributes:
        indexer (Indexer): The indexer used for processing documents.
        logger (logging.Logger): Logger for tracking indexing process.
    """

    def __init__(self, indexer: IndexerService):
        """
        Initialize the WebsiteIndexer.

        Args:
            indexer (Indexer): Indexer to use for document processing.
        """
        self.indexer = indexer
        self.logger = logger

    def _fetch_sitemap(self, base_url: str) -> List[str]:
        """
        Fetch and parse sitemap URLs.

        Args:
            base_url (str): Base URL to fetch sitemap from.

        Returns:
            List[str]: List of URLs from the sitemap.
        """
        sitemap_url = urljoin(base_url, "sitemap.xml")

        try:
            response = requests.get(sitemap_url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            urls = [
                loc.text
                for loc in root.findall(
                    ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
                )
                if loc.text and not loc.text.endswith(".pdf")
            ]

            self.logger.info(f"Found {len(urls)} urls in sitemap")
            return urls

        except Exception:
            self.logger.info(f"No sitemap found for {base_url}")
            return []

    def _process_url(self, url: str) -> None:
        """
        Process a single URL for indexing.

        Args:
            url (str): URL to process and index.
        """
        self.logger.info(f"Loading website: {url}")

        try:
            loader = WebBaseLoader(url)
            docs = loader.load()

            if not self.indexer.text_splitter:
                raise RuntimeError("Text Splitter not initialized.")

            if not self.indexer.vector_store:
                raise RuntimeError("Vector Store not initialized.")

            self.logger.info("Splitting docs into chunks")
            chunks = self.indexer.text_splitter.split_documents(docs)
            self.logger.info(f"Split into {len(chunks)} chunks")

            self.indexer.vector_store.add_documents(chunks)
            self.logger.info("Indexing complete for URL")

        except Exception as e:
            self.logger.error(f"Error processing URL {url}: {e}")

    def index_website(self, base_url: str) -> None:
        """
        Index a website, using sitemap if available.

        Args:
            base_url (str): Base URL of the website to index.
        """
        self.logger.info(f"Processing website: {base_url}")

        # Fetch sitemap URLs or use base URL
        sitemap_urls = self._fetch_sitemap(base_url) or [base_url]

        # Process each URL
        for url in sitemap_urls:
            self._process_url(url)


def load_website(url: str, indexer: IndexerService) -> None:
    """
    Convenience function to index a website using WebsiteIndexer.

    Args:
        url (str): Base URL of the website to index.
        indexer (Indexer): Indexer to use for document processing.
    """
    website_indexer = WebsiteIndexer(indexer)
    website_indexer.index_website(url)
