"""
Document Routes Module

This module defines the API routes for document processing operations,
with support for concurrent document processing from multiple users.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from src.services.document_service import process_document
from src.services.indexer_service import IndexerService
from src.utils.dependency import get_indexer
from src.utils.logger import get_logger

# Initialize logger for the routes
logger = get_logger("DocumentRoutes")


class DocumentProcessRequest(BaseModel):
    """Request model for document processing."""

    file: UploadFile


router = APIRouter(
    prefix="/document",
    tags=["document"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)


@router.post(
    "/",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request parameters"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid file format"},
    },
)
async def process_document_endpoint(
    file: UploadFile = File(...), indexer: IndexerService = Depends(get_indexer)
) -> Dict[str, Any]:
    """
    Process an uploaded document file synchronously with concurrent user support.

    Args:
        file (UploadFile): The uploaded file to process
        indexer (IndexerService): Service for indexing document content

    Returns:
        Dict[str, Any]: Processing results including status and metadata

    Raises:
        HTTPException: If document processing fails
    """
    try:
        logger.info(f"Processing document: {file.filename}")

        if not file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File not found. Please upload the file to process",
            )

        # Read file content
        content = await file.read()

        # Process the document and wait for result
        result = await process_document(
            content, file.filename, file.content_type, indexer
        )

        logger.info(f"Successfully processed document: {file.filename}")
        return result

    except Exception as e:
        error_msg = f"Error processing document {file.filename}: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )
