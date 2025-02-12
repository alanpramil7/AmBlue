"""
Wiki Routes Module

This module defines the API routes for processing wiki operations,
including website indexing and management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.documents import Document
from pydantic import BaseModel, Field

from src.services.indexer_service import IndexerService
from src.services.wiki_service import fetch_wiki_pages
from src.utils.dependency import get_indexer
from src.utils.logger import logger


class WikiProcessingRequest(BaseModel):
    """
    Pydantic model for wiki processing request.

    Attributes:
        organization (str): Name of the organization
        project (str): Name of the project
        wikiIdentifier (str): Unique identifier for the wiki
    """

    organization: str = Field(default="cloudcadi", description="Organization name")
    project: str = Field(default="CloudCADI", description="Project name")
    wikiIdentifier: str = Field(default="CloudCADI.wiki", description="Wiki Identifier")


# Create router with prefix and tags for API documentation
router = APIRouter(
    prefix="/wiki",
    tags=["wiki"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@router.post("/")
async def process_website(
    request: WikiProcessingRequest, indexer: IndexerService = Depends(get_indexer)
) -> dict:
    """
    Process and index wiki pages from a specified repository.

    Args:
        request (WikiProcessingRequest): Request containing organization, project and wiki details
        indexer (IndexerService): Service for managing vector store operations

    Returns:
        dict: Response containing processing status and statistics

    Raises:
        HTTPException: If wiki pages are not found or vector store is not initialized
    """
    try:
        # Process wiki pages using the provided parameters
        pages = await fetch_wiki_pages(
            request.organization, request.project, request.wikiIdentifier
        )

        # Check if any pages were found
        if pages is None:
            logger.info("No Pages found.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No wiki pages found"
            )

        # Verify vector store initialization
        if not indexer.vector_store:
            logger.error("Vector store not initialized")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Vector store not initialized",
            )

        total_docs = 0

        # Process each wiki page
        for page in pages:
            wiki_content = page.content

            # Split content into lines and remove empty ones
            lines = [line.strip() for line in wiki_content.split("\n")]
            non_empty_lines = [line for line in lines if line]

            # Skip processing if content meets certain criteria
            if not non_empty_lines:
                logger.info(f"Skipping empty content for page: {page.page_path}")
                continue

            # Skip single-line content that's just a heading or image
            if len(non_empty_lines) == 1:
                line = non_empty_lines[0]
                if line.startswith("#") or line.startswith("!["):
                    logger.info(
                        f"Skipping single heading/image content for page: {page.page_path}"
                    )
                    continue

            # Create document with metadata and add to vector store
            doc = Document(
                page_content=wiki_content,
                metadata={
                    "source": f"wiki_{page.page_path}",
                    "organization": request.organization,
                    "project": request.project,
                },
            )
            await indexer.vector_store.aadd_documents([doc])
            total_docs += 1
            logger.info(f"Added document to vector store: {page.page_path}")

        return {"status": "success", "total_documents_processed": total_docs}

    except Exception as e:
        logger.error(f"Error processing wiki: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing wiki: {str(e)}",
        )
