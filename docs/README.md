# AmBlue RAG Application

AmBlue is a Retrieval-Augmented Generation (RAG) application that provides website content indexing and retrieval capabilities. The application is built using FastAPI and integrates with various components for document processing, embedding generation, and vector storage.

## Overview

AmBlue allows users to:

- Process and index website content
- Handle sitemap-based website crawling
- Store and manage document embeddings
- Provide API endpoints for content processing

## Key Features

- Website content processing with sitemap support
- Azure DevOps wiki integration and processing
- Document processing (PDF, DOCX)
- Document chunking and embedding generation
- Vector storage using ChromaDB
- RESTful API interface
- Health monitoring endpoints

## Technical Stack

- **Framework**: FastAPI
- **Embedding Model**: Ollama (nomic-embed-text)
- **Vector Store**: ChromaDB
- **Document Processing**: LangChain
- **Web Crawling**: Custom implementation with sitemap support

## Documentation Index

- [Architecture Overview](./ARCHITECTURE.md)
- [API Documentation](./API.md)
- [Services Documentation](./SERVICES.md)
- [Setup Guide](./SETUP.md)

## Quick Start

1. Clone the repository
2. Install dependencies: `uv sync`
3. Set up environment variables
4. Run the application: `uvicorn src.__main__:app --reload`
