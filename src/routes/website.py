"""
Website Routes Module

This module defines the API routes for website processing operations,
including website indexing and management endpoints with concurrent processing support.
"""

from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from src.services.indexer_service import IndexerService
from src.services.website_service import WebsiteIndexer
from src.utils.dependency import get_indexer
from src.utils.logger import logger


class WebsiteProcessRequest(BaseModel):
    """Request model for website processing."""

    url: HttpUrl

    class Config:
        json_schema_extra = {"example": {"url": "https://example.com"}}


router = APIRouter(
    prefix="/website",
    tags=["website"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


async def process_website_background(url: str, indexer: IndexerService) -> None:
    """
    Background task for processing websites.

    Args:
        url (str): The website URL to process
        indexer (IndexerService): The indexer service instance
    """
    try:
        website_indexer = WebsiteIndexer(indexer)
        await website_indexer.index_website(url)
        logger.info(f"Successfully processed website: {url}")
    except Exception as e:
        logger.error(f"Error in background processing of website {url}: {e}")


@router.post(
    "/",
    response_model=Dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process Website",
    description="Processes and indexes the content of the specified website asynchronously.",
)
async def process_website(
    request: WebsiteProcessRequest,
    background_tasks: BackgroundTasks,
    indexer: IndexerService = Depends(get_indexer),
) -> Dict:
    """
    Process and index a website asynchronously.

    Args:
        request (WebsiteProcessRequest): The request containing the website URL
        background_tasks (BackgroundTasks): FastAPI background tasks handler
        indexer (IndexerService): The indexer service instance

    Returns:
        Dict: Response indicating the task has been queued

    Raises:
        HTTPException: If the URL is missing or invalid
    """
    try:
        logger.info(f"Queueing website processing request for URL: {request.url}")

        if not request.url:
            logger.error("Missing URL in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required."
            )

        # Add the processing task to background tasks
        background_tasks.add_task(process_website_background, str(request.url), indexer)

        return {
            "status": "accepted",
            "message": f"Website {request.url} has been queued for processing",
        }

    except Exception as e:
        logger.error(f"Error queueing website {request.url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue website processing: {str(e)}",
        )
