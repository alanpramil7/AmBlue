"""
Main application module for AmBlue API service.

This module initializes and configures the FastAPI application,
sets up environment variables, and provides the main entry point
for running the service.
"""

from dotenv import load_dotenv

# Load environment variables from .env file at startup
load_dotenv()

import uvicorn
from fastapi import FastAPI

from src.routes import agent, document, website, wiki


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application instance.

    This function initializes the FastAPI application with basic metadata
    and registers the health check endpoint.

    Returns:
        FastAPI: Configured FastAPI application instance
    """
    application = FastAPI(
        title="AmBlue",
        version="0.1",
        description="Amadis AI Agent",
        # Additional FastAPI configurations can be added here
        docs_url="/docs",  # Swagger UI endpoint
        redoc_url="/redoc",  # ReDoc endpoint
    )

    @application.get(
        path="/check-health",
        tags=["Health"],
        summary="Health Check Endpoint",
        description="Returns the current status and version of the service",
    )
    async def check_health() -> dict:
        """
        Health check endpoint to verify service status.

        Returns:
            dict: Dictionary containing service status and version information
        """
        return {
            "status": "Healthy",
            "version": "0.1",
        }

    application.include_router(website.router)
    application.include_router(wiki.router)
    application.include_router(document.router)
    application.include_router(agent.router)

    return application


# Create the FastAPI application instance
app = create_app()

# Main entry point for running the application
if __name__ == "__main__":
    """
    Development server configuration.

    Run the application using uvicorn server with hot reload enabled
    for development purposes.
    """
    uvicorn.run(
        app=app,
        host="localhost",  # Local development host
        port=8000,  # Default port for the service
        reload=True,  # Enable auto-reload for development
        log_level="info",  # Set logging level
    )
