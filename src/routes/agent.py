# """
# Agent Routes Module

# This module defines the API routes for document processing operations,
# including file upload and indexing endpoints.
# """

# from fastapi import APIRouter, Depends, HTTPException, status
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel

# from src.services.agent_service import AgentService
# from src.services.indexer_service import IndexerService
# from src.utils.dependency import get_indexer
# from src.utils.logger import get_logger

# # Initialize logger for the routes
# logger = get_logger("DocumentRoutes")
# agent_service = AgentService()


# class AgentProcessingRequest(BaseModel):
#     """
#     Request model for document processing.

#     Attributes:
#         file (UploadFile): The uploaded file to be processed
#     """

#     quesiton: str


# # Create router with prefix and tags for API documentation
# router = APIRouter(
#     prefix="/agent",
#     tags=["agent"],
#     responses={
#         status.HTTP_404_NOT_FOUND: {"description": "Not found"},
#         status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
#     },
# )


# async def format_sse(data: str) -> str:
#     """Format data as SSE message"""
#     return f"data: {data}\n\n"


# @router.post(
#     "/",
#     responses={
#         status.HTTP_400_BAD_REQUEST: {"description": "Invalid request parameters"},
#         status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid file format"},
#     },
# )
# async def generate_response(request: AgentProcessingRequest) -> StreamingResponse:
#     """ """
#     try:
#         return StreamingResponse(
#             agent_service.stream_response(request.quesiton),
#             media_type="text/event-stream",
#         )
#     except Exception as e:
#         error_msg = f"Error processing document {str(e)}"
#         logger.error(error_msg)

#         # Raise HTTP exception with detailed error message
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=error_msg,
#         )"""
"""
Agent Routes Module

This module defines the API routes for agent operations,
handling question answering through server-sent events (SSE).
"""

import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.services.agent_service import AgentService
from src.utils.logger import get_logger

# Initialize logger for the routes
logger = get_logger("AgentRoutes", logging.INFO)


class AgentProcessingRequest(BaseModel):
    """
    Request model for agent processing.

    Attributes:
        question (str): The question to be processed by the agent
    """
    question: str = Field(..., description="The question to be answered by the agent")

    class Config:
        """Pydantic model configuration"""
        json_schema_extra = {
            "example": {
                "question": "What is the capital of France?"
            }
        }


# Create router with prefix and tags for API documentation
router = APIRouter(
    prefix="/agent",
    tags=["agent"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)

# Initialize agent service
agent_service = AgentService()


async def format_sse(data: str) -> str:
    """
    Format data as Server-Sent Events (SSE) message.

    Args:
        data (str): The data to be formatted

    Returns:
        str: Formatted SSE message
    """
    return f"data: {data}\n\n"


@router.post(
    "/",
    response_class=StreamingResponse,
    summary="Generate Agent Response",
    description="Generates a streaming response for the given question using the agent.",
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid request parameters"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Invalid request format"},
    },
)
async def generate_response(request: AgentProcessingRequest) -> StreamingResponse:
    """
    Generate streaming response for the given question.

    Args:
        request (AgentProcessingRequest): The request containing the question

    Returns:
        StreamingResponse: Server-sent events stream with agent's response

    Raises:
        HTTPException: If there's an error processing the request
    """
    try:
        # Log the incoming request
        logger.info(f"Processing question: {request.question}")

        # Validate question
        if not request.question.strip():
            logger.error("Empty question in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty."
            )

        # Generate streaming response
        response = StreamingResponse(
            agent_service.stream_response(request.question),
            media_type="text/event-stream"
        )

        # Log successful processing
        logger.info("Successfully initiated response streaming")

        return response

    except Exception as e:
        error_msg = f"Error processing question: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
