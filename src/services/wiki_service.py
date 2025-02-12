import asyncio
import json
import os
from asyncio import Semaphore
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import aiohttp
import cachetools
from aiohttp import ClientSession, TCPConnector

from src.utils.logger import logger


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
