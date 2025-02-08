"""
Website Routes Module

This module defines the API routes for website processing operations,
including website indexing and management endpoints.
"""

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from src.services.indexer_service import IndexerService
from src.services.website_service import load_website
from src.utils.dependency import get_indexer
from src.utils.logger import get_logger

# Initialize logger for the routes
logger = get_logger("WebsiteRoutes")


class WebsiteProcessRequest(BaseModel):
    """
    Request model for website processing.

    Attributes:
        url (HttpUrl): The URL of the website to process.
                      Using HttpUrl for automatic URL validation.
    """

    url: HttpUrl

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {"example": {"url": "https://example.com"}}


# Create router with prefix and tags for API documentation
router = APIRouter(
    prefix="/website",
    tags=["website"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@router.post(
    "/",
    response_model=Dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process Website",
    description="Processes and indexes the content of the specified website.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request parameters"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid URL format"},
    },
)
async def process_website(
    request: WebsiteProcessRequest, indexer: IndexerService = Depends(get_indexer)
) -> Dict:
    """
    Process and index a website.

    Args:
        request (WebsiteProcessRequest): The request containing the website URL
        indexer (IndexerService): The indexer service instance

    Returns:
        Dict: Empty dictionary on successful processing

    Raises:
        HTTPException: If the URL is missing or invalid
        HTTPException: If there's an error processing the website
    """
    try:
        # Log the incoming request
        logger.info(f"Processing website request for URL: {request.url}")

        # Validate URL (additional validation if needed beyond Pydantic)
        if not request.url:
            logger.error("Missing URL in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required."
            )

        # Process the website
        load_website(str(request.url), indexer)

        # Log successful processing
        logger.info(f"Successfully processed website: {request.url}")

        return {
            "status": "success",
            "message": f"Website {request.url} has been processed",
        }

    except Exception as e:
        # Log the error
        logger.error(f"Error processing website {request.url}: {e}")

        # Raise HTTP exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process website: {str(e)}",
        )
