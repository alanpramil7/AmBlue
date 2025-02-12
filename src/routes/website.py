"""
Website Routes Module with concurrent request handling
"""

import asyncio
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field, HttpUrl

from src.services.indexer_service import IndexerService
from src.services.website_service import process_website_pages
from src.utils.dependency import get_indexer
from src.utils.logger import logger


class WebsiteProcessingRequest(BaseModel):
    """Pydantic model for website processing request."""

    url: HttpUrl = Field(..., description="Website URL to process")
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent requests"
    )

    class Config:
        json_schema_extra = {"example": {"url": "https://example.com"}}


# Track ongoing processing tasks
processing_tasks: Dict[str, asyncio.Task] = {}


router = APIRouter(
    prefix="/website",
    tags=["website"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


async def process_website_task(
    request: WebsiteProcessingRequest, indexer: IndexerService, task_id: str
) -> dict:
    """
    Background task to process and index website pages.
    """
    try:
        result = await process_website_pages(
            str(request.url), indexer, request.max_concurrent_requests
        )

        if not result:
            logger.info("No pages processed")
            return {"status": "completed", "total_documents_processed": 0}

        return {
            "status": "completed",
            "total_documents_processed": result["processed_pages"],
            "urls_processed": result["processed_urls"],
        }

    except Exception as e:
        logger.error(f"Error processing website: {str(e)}")
        return {"status": "failed", "error": str(e)}


@router.post("/")
async def start_website_processing(
    request: WebsiteProcessingRequest,
    background_tasks: BackgroundTasks,
    indexer: IndexerService = Depends(get_indexer),
) -> dict:
    """
    Start asynchronous processing of website pages.
    """
    # Generate unique task ID from URL
    task_id = str(request.url).replace("://", "_").replace("/", "_")

    # Check if already processing
    if task_id in processing_tasks:
        return {
            "status": "in_progress",
            "message": "Processing already in progress for this website",
            "task_id": task_id,
        }

    # Create and store the processing task
    task = asyncio.create_task(process_website_task(request, indexer, task_id))
    processing_tasks[task_id] = task

    return {
        "status": "started",
        "message": "Website processing started",
        "task_id": task_id,
    }


@router.get("/status/{task_id}")
async def get_processing_status(task_id: str) -> dict:
    """
    Get the status of a processing task.
    """
    task = processing_tasks.get(task_id)
    if not task:
        return {
            "status": "completed",
            "message": "No active processing task found with this ID",
        }

    if task.done():
        try:
            result = await task
            return result
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    return {"status": "in_progress", "message": "Processing in progress"}
