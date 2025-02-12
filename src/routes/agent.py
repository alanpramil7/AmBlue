"""
Agent Routes Module

This module defines the API routes for agent operations,
handling question answering through server-sent events (SSE).
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from src.services.agent_service import AgentService
from src.utils.logger import logger


class AgentProcessingRequest(BaseModel):
    """
    Request model for agent processing.

    Attributes:
        question (str): The question to be processed by the agent
        user_id (str): The ID of the user making the request
    """

    question: str = Field(..., description="The question to be answered by the agent")
    user_id: str = Field(..., description="The ID of the user making the request")

    class Config:
        """Pydantic model configuration"""

        json_schema_extra = {
            "example": {
                "question": "What is the capital of France?",
                "user_id": "user123",
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
        # Log the incoming request with more detail
        logger.info(
            f"Received request - Question: {request.question}, User ID: {request.user_id}"
        )

        # Validate input data more thoroughly
        if not isinstance(request.question, str) or not isinstance(
            request.user_id, str
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid data types: question and user_id must be strings",
            )

        # Validate question
        if not request.question.strip():
            logger.error("Empty question in request")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question cannot be empty.",
            )

        # Generate streaming response
        response = StreamingResponse(
            agent_service.stream_response(request.question, request.user_id),
            media_type="text/event-stream",
        )

        # Log successful processing
        logger.info("Successfully initiated response streaming")

        return response

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        error_msg = f"Error processing question: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg
        )
