# AmBlue RAG Application

AmBlue is a Retrieval-Augmented Generation (RAG) application that provides intelligent document processing, website content indexing, and Azure DevOps Wiki integration capabilities. Built with FastAPI, it offers a robust API for content processing and retrieval.

## Features

- Website content processing and indexing
  - Sitemap-based crawling
  - Concurrent processing with rate limiting
  - Progress tracking
- Azure DevOps Wiki integration
  - Full wiki content processing
  - Hierarchical structure preservation
  - Caching for improved performance
- Document processing
  - Support for multiple formats (PDF, DOCX)
  - Intelligent chunking
  - Vector embeddings generation
- Vector storage using ChromaDB
- RESTful API with full documentation
- Health monitoring and metrics

## Quick Start

1. **Prerequisites**
   - Python 3.10 or higher
   - uv package manager
   - Ollama (for embeddings)
   - ChromaDB

2. **Installation**
   ```bash
   # Clone the repository
   git clone [repository-url]
   cd amblue

   # Install dependencies
   uv sync
   ```

3. **Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your configuration
   ```

4. **Running the Application**
   ```bash
   # Development mode
   uvicorn src.__main__:app --reload

   # Production mode
   uvicorn src.__main__:app
   ```

5. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - ReDoc Interface: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/check-health

## Documentation

Detailed documentation is available in the `docs` directory:

- [Architecture Overview](docs/ARCHITECTURE.md)
- [API Documentation](docs/API.md)
- [Services Documentation](docs/SERVICES.md)
