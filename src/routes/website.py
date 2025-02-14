from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from src.services.indexer_service import IndexerService
from src.services.database_service import DatabaseService
from src.services.website_service import WebsiteService
from src.utils.dependency import get_indexer, get_database
from src.utils.logger import logger


class WebsiteProcessingRequest(BaseModel):
    """Pydantic model for website processing request."""

    url: HttpUrl = Field(..., description="Website URL to process")
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent requests"
    )

    class Config:
        json_schema_extra = {"example": {"url": "https://example.com"}}


class ProcessingStatusResponse(BaseModel):
    """Pydantic model for processing status response."""

    status: str
    total_urls: int
    processed_urls: list[str]
    remaining_urls: list[str]
    failed_urls: list[str]
    current_url: str | None
    percent_complete: float
    error: str | None


# Initialize router
router = APIRouter(prefix="/website", tags=["website"])


def get_processor(
    indexer: IndexerService = Depends(get_indexer),
    database: DatabaseService = Depends(get_database),
) -> WebsiteService:
    return WebsiteService(indexer, database)


@router.post("/", response_model=dict)
async def start_website_processing(
    request: WebsiteProcessingRequest,
    processor: WebsiteService = Depends(get_processor),
    database: DatabaseService = Depends(get_database),
) -> dict:
    """
    Start website processing and return task ID for status tracking.
    """
    try:
        # Check if URL is already being processed
        existing_task = database.get_task_by_url(str(request.url))
        if existing_task:
            logger.info("Website is already processed.")
            return {
                "status": existing_task["status"],
                "task_id": existing_task["task_id"],
                "message": "Website is already being processed or processed.",
            }

        # Start new processing task - the processor will create the task record
        task_id = await processor.process_website(str(request.url))
        return {
            "status": "started",
            "task_id": task_id,
            "message": "Website processing started",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/status/{task_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(
    task_id: str, database: DatabaseService = Depends(get_database)
) -> ProcessingStatusResponse:
    """
    Get detailed processing status for frontend tracking.
    """
    task = database.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return ProcessingStatusResponse(
        status=task["status"]["status"].value,
        total_urls=task["status"]["total_urls"],
        processed_urls=task["status"]["processed_urls"],
        remaining_urls=task["status"]["remaining_urls"],
        failed_urls=task["status"]["failed_urls"],
        current_url=task["status"]["current_url"],
        percent_complete=task["status"]["percent_complete"],
        error=task["status"]["error"],
    )
