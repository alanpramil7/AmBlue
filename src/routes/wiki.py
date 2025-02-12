"""
Wiki Routes Module with concurrent request handling
"""

from fastapi import APIRouter, Depends, status, BackgroundTasks
from langchain_core.documents import Document
from pydantic import BaseModel, Field
import asyncio
from typing import Dict

from src.services.indexer_service import IndexerService
from src.services.wiki_service import fetch_wiki_pages
from src.utils.dependency import get_indexer
from src.utils.logger import logger


class WikiProcessingRequest(BaseModel):
    """Pydantic model for wiki processing request."""

    organization: str = Field(default="cloudcadi", description="Organization name")
    project: str = Field(default="CloudCADI", description="Project name")
    wikiIdentifier: str = Field(default="CloudCADI.wiki", description="Wiki Identifier")
    max_concurrent_requests: int = Field(
        default=10, description="Maximum concurrent requests"
    )


# Track ongoing processing tasks
processing_tasks: Dict[str, asyncio.Task] = {}


router = APIRouter(
    prefix="/wiki",
    tags=["wiki"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


async def process_wiki_pages(
    request: WikiProcessingRequest, indexer: IndexerService, task_id: str
) -> dict:
    """
    Background task to process and index wiki pages.
    """
    try:
        pages = await fetch_wiki_pages(
            request.organization,
            request.project,
            request.wikiIdentifier,
            request.max_concurrent_requests,
        )

        if not pages:
            logger.info("No Pages found.")
            return {"status": "completed", "total_documents_processed": 0}

        if not indexer.vector_store:
            logger.error("Vector store not initialized")
            return {"status": "failed", "error": "Vector store not initialized"}

        # Process pages in chunks to avoid memory issues
        chunk_size = 10
        total_docs = 0

        for i in range(0, len(pages), chunk_size):
            chunk = pages[i : i + chunk_size]
            docs = []

            for page in chunk:
                if not page.content.strip():
                    continue

                lines = [line.strip() for line in page.content.split("\n")]
                non_empty_lines = [line for line in lines if line]

                if not non_empty_lines:
                    continue

                if len(non_empty_lines) == 1:
                    line = non_empty_lines[0]
                    if line.startswith("#") or line.startswith("!["):
                        continue

                doc = Document(
                    page_content=page.content,
                    metadata={
                        "source": f"wiki_{page.page_path}",
                        "organization": request.organization,
                        "project": request.project,
                    },
                )
                docs.append(doc)

            if docs:
                await indexer.vector_store.aadd_documents(docs)
                total_docs += len(docs)
                logger.info(f"Processed chunk of {len(docs)} documents")

        logger.info(
            f"Wiki processing completed. Total documents processed: {total_docs}"
        )
        return {"status": "completed", "total_documents_processed": total_docs}

    except Exception as e:
        logger.error(f"Error processing wiki: {str(e)}")
        return {"status": "failed", "error": str(e)}
    # finally:
    #     # Clean up task tracking
    #     if task_id in processing_tasks:
    #         del processing_tasks[task_id]


@router.post("/")
async def process_website(
    request: WikiProcessingRequest,
    background_tasks: BackgroundTasks,
    indexer: IndexerService = Depends(get_indexer),
) -> dict:
    """
    Start asynchronous processing of wiki pages.
    """
    # Generate unique task ID
    task_id = f"{request.organization}_{request.project}_{request.wikiIdentifier}"

    # Check if already processing
    if task_id in processing_tasks:
        return {
            "status": "in_progress",
            "message": "Processing already in progress for this wiki",
            "task_id": task_id,
        }

    # Create and store the processing task
    task = asyncio.create_task(process_wiki_pages(request, indexer, task_id))
    processing_tasks[task_id] = task

    return {
        "status": "started",
        "message": "Wiki processing started",
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
