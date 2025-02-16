"""
Wiki Routes Module with concurrent request handling
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.services.database_service import DatabaseService
from src.services.indexer_service import IndexerService
from src.services.wiki_service import WikiService
from src.utils.dependency import get_database, get_indexer
from src.utils.logger import logger


class WikiProcessingRequest(BaseModel):
    """Pydantic model for wiki processing request."""

    organization: str = Field(default="cloudcadi", description="Organization name")
    project: str = Field(default="CloudCADI", description="Project name")
    wikiIdentifier: str = Field(default="CloudCADI.wiki", description="Wiki Identifier")
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent requests"
    )


class ProcessingStatusResponse(BaseModel):
    """Pydantic model for processing status response."""

    status: str
    total_pages: int
    processed_pages: list[str]
    remaining_pages: list[str]
    failed_pages: list[str]
    current_page: str | None
    percent_complete: float
    error: str | None


router = APIRouter(
    prefix="/wiki",
    tags=["wiki"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


def get_processor(
    indexer: IndexerService = Depends(get_indexer),
    database: DatabaseService = Depends(get_database),
) -> WikiService:
    return WikiService(indexer, database)


@router.post("/", response_model=dict)
async def start_wiki_processing(
    request: WikiProcessingRequest,
    processor: WikiService = Depends(get_processor),
    database: DatabaseService = Depends(get_database),
) -> dict:
    """
    Start wiki processing and return task ID for status tracking.
    """
    try:
        task_id = (
            f"{request.organization.lower()}_{request.project}_{request.wikiIdentifier}"
        )
        existing_task = database.get_wiki_task_by_details(
            request.organization, request.project, request.wikiIdentifier
        )

        if existing_task:
            return {
                "status": existing_task["status"],
                "task_id": existing_task["task_id"],
                "message": "Wiki is already being processed or processed",
            }

        task_id = await processor.process_wiki(
            request.organization,
            request.project,
            request.wikiIdentifier,
            request.max_concurrent_requests,
        )
        return {
            "status": "started",
            "task_id": task_id,
            "message": "Wiki processing started",
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
    logger.info(f"Getting status for task: {task_id}")
    task = database.get_wiki_task(task_id)
    if not task:
        logger.error(f"Task not found: {task_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # logger.info(f"Found task status: {task['status']}")
    return ProcessingStatusResponse(
        status=task["status"]["status"].value,
        total_pages=task["status"]["total_pages"],
        processed_pages=task["status"]["processed_pages"],
        remaining_pages=task["status"]["remaining_pages"],
        failed_pages=task["status"]["failed_pages"],
        current_page=task["status"]["current_page"],
        percent_complete=task["status"]["percent_complete"],
        error=task["status"]["error"],
    )
