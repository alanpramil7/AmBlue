"""
DevOps Wiki Client Module

This module provides functionality to retrieve and process wiki pages
from Azure DevOps repositories using the Azure DevOps REST API.

Key Features:
- Retrieve wiki page contents
- Fetch entire wiki page tree
- Support for recursive page retrieval
- Robust error handling and logging
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from src.utils.logger import logger


@dataclass
class WikiPage:
    """
    Represents a single wiki page with its metadata and content.

    Attributes:
        page_path (str): Full path of the wiki page in the repository
        content (str): Markdown or text content of the page
        remote_url (Optional[str]): External URL of the wiki page, if available
    """

    page_path: str
    content: str
    remote_url: Optional[str] = None


class WikiClientError(Exception):
    """Custom exception for Wiki Client related errors."""

    pass


class WikiClient:
    """
    Client for interacting with Azure DevOps Wiki REST API.
    Handles authentication, page retrieval, and wiki tree navigation.
    """

    def __init__(
        self,
        organization: str,
        project: str,
        wiki_identifier: str,
        personal_access_token: str,
    ):
        """
        Initialize the Wiki Client with Azure DevOps credentials.

        Args:
            organization (str): Azure DevOps organization name
            project (str): Project name
            wiki_identifier (str): Specific wiki repository identifier
            personal_access_token (str): Authentication token
        """
        logger.info(
            f"Initializing WikiClient for organization: {organization}, project: {project}"
        )
        self.base_url = f"https://dev.azure.com/{organization}/{project}/_apis/wiki/wikis/{wiki_identifier}/pages"
        self.auth = ("", personal_access_token)
        self.api_version = "7.1"
        logger.info(f"Base URL configured: {self.base_url}")

    def _make_api_request(
        self, params: Dict[str, Any], method: str = "GET"
    ) -> Optional[Dict[str, Any]]:
        """
        Makes API requests with consistent error handling.

        Args:
            params (Dict[str, Any]): Query parameters for the request
            method (str, optional): HTTP method. Defaults to 'GET'

        Returns:
            Optional[Dict[str, Any]]: Parsed JSON response or None if request fails
        """
        logger.info(f"Making {method} request to {self.base_url}")
        logger.info(f"Request parameters: {params}")

        try:
            params["api-version"] = self.api_version

            if method == "GET":
                response = requests.get(self.base_url, params=params, auth=self.auth)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            logger.info(f"Request successful. Status code: {response.status_code}")
            return response.json()

        except requests.RequestException as e:
            logger.error(f"API Request failed: {str(e)}")
            logger.info(f"Request details - URL: {self.base_url}, Params: {params}")
            return None

    def _get_page_content(self, page_path: str) -> str:
        """
        Retrieves the content for a specific wiki page.

        Args:
            page_path (str): Path of the wiki page

        Returns:
            str: Page content or empty string if retrieval fails
        """
        logger.info(f"Fetching content for page: {page_path}")
        params = {"path": page_path, "includeContent": True}

        result = self._make_api_request(params)
        if result:
            logger.info(f"Successfully retrieved content for page: {page_path}")
            return result.get("content", "")
        else:
            logger.warning(f"Failed to retrieve content for page: {page_path}")
            return ""

    def _get_wiki_tree(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the complete wiki page tree from the root.

        Returns:
            Optional[Dict[str, Any]]: Entire wiki page tree structure or None if retrieval fails
        """
        logger.info("Retrieving complete wiki page tree")
        params = {"path": "/", "recursionLevel": "full", "includeContent": True}

        result = self._make_api_request(params)
        if result:
            logger.info("Successfully retrieved wiki tree structure")
            logger.info(f"Wiki tree size: {len(str(result))} bytes")
        else:
            logger.error("Failed to retrieve wiki tree")
        return result

    def _flatten_pages(self, page: Dict[str, Any]) -> List[WikiPage]:
        """
        Recursively flattens the wiki page tree into a list of WikiPage objects.

        Args:
            page (Dict[str, Any]): Root page or subpage to process

        Returns:
            List[WikiPage]: Flattened list of wiki pages
        """
        pages = []
        page_path = page.get("path", "/")
        content = page.get("content")
        remote_url = page.get("remoteUrl")

        logger.info(f"Processing page: {page_path}")

        if not content:
            logger.info(
                f"Content not found in tree for {page_path}, fetching separately"
            )
            content = self._get_page_content(page_path)

        if content:
            logger.info(f"Adding page to collection: {page_path}")
            pages.append(
                WikiPage(page_path=page_path, content=content, remote_url=remote_url)
            )
        else:
            logger.warning(f"No content found for page: {page_path}")

        # Process subpages recursively
        subpages = page.get("subPages", [])
        logger.info(f"Processing {len(subpages)} subpages for {page_path}")
        for subpage in subpages:
            pages.extend(self._flatten_pages(subpage))

        return pages


def fetch_wiki_pages(
    organization: str, project: str, wiki_identifier: str
) -> Optional[List[WikiPage]]:
    """
    Main entry point to fetch all wiki pages for a given Azure DevOps wiki.

    Args:
        organization (str): Azure DevOps organization name
        project (str): Project name
        wiki_identifier (str): Specific wiki repository identifier

    Returns:
        Optional[List[WikiPage]]: List of wiki pages or None if retrieval fails
    """
    logger.info(f"Starting wiki page fetch for {organization}/{project}")

    access_token = os.getenv("WIKI_ACCESS_TOKEN")
    if not access_token:
        logger.error("WIKI_ACCESS_TOKEN environment variable not set")
        return None

    try:
        logger.info("Initializing Wiki Client")
        client = WikiClient(organization, project, wiki_identifier, access_token)

        logger.info("Retrieving wiki tree")
        wiki_tree = client._get_wiki_tree()

        if wiki_tree:
            logger.info("Successfully retrieved wiki tree, processing pages")
            pages = client._flatten_pages(wiki_tree)
            logger.info(f"Successfully processed {len(pages)} wiki pages")
            return pages
        else:
            logger.error("Failed to retrieve wiki tree")
            return None

    except Exception as e:
        logger.error(f"Wiki page retrieval failed with error: {str(e)}")
        logger.exception("Detailed error trace:")
        return None
