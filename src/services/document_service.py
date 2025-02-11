import asyncio
import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Union

import aiofiles
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from langchain_core.documents.base import Document

from src.services.indexer_service import IndexerService
from src.utils.dependency import get_indexer
from src.utils.logger import get_logger

# Initialize logger
logger = get_logger("DocumentService", logging.INFO)


class DocumentService:
    """Service class for handling concurrent document processing operations."""

    def __init__(self):
        """Initialize DocumentService with dependencies and supported formats."""
        logger.info("Initializing DocumentService")
        self.indexer = get_indexer()
        self.supported_extensions = {"pdf": PyPDFLoader, "docx": Docx2txtLoader}
        # Semaphore to limit concurrent processing
        self.semaphore = asyncio.Semaphore(
            5
        )  # Adjust number based on your server capacity
        logger.info(
            f"Supported file extensions: {', '.join(self.supported_extensions.keys())}"
        )

    async def _create_document(self, file_path: str) -> List[Document]:
        """
        Create document objects from the input file asynchronously.

        Args:
            file_path (str): Path to the document file

        Returns:
            List[Document]: List of created document objects

        Raises:
            ValueError: If file format is not supported
        """
        logger.info(f"Creating document objects from file: {file_path}")

        extension = Path(file_path).suffix.lower().lstrip(".")
        logger.debug(f"Detected file extension: {extension}")

        if extension not in self.supported_extensions:
            error_msg = (
                f"Unsupported file format: {extension}. "
                f"Supported formats are: {', '.join(self.supported_extensions.keys())}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        loader_class = self.supported_extensions[extension]
        logger.info(f"Using loader class: {loader_class.__name__}")

        try:
            # Run document loading in a thread pool
            documents = await asyncio.to_thread(loader_class(file_path).load)
            logger.info(f"Successfully created {len(documents)} document objects")
            return documents
        except Exception as e:
            logger.error(f"Failed to load document: {str(e)}")
            raise

    async def process_document(self, file_path: str) -> Dict[str, Union[str, int]]:
        """
        Process and index a document with concurrent processing support.

        Args:
            file_path (str): Path to the document file

        Returns:
            Dict[str, Union[str, int]]: Processing result containing status and metrics

        Raises:
            RuntimeError: If indexer components are not properly initialized
        """
        async with self.semaphore:  # Limit concurrent processing
            logger.info(f"Starting document processing for: {file_path}")

            if not self.indexer.text_splitter or not self.indexer.vector_store:
                error_msg = "Indexer components not properly initialized"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            try:
                # Document processing pipeline with async operations
                docs = await self._create_document(file_path)

                logger.info("Splitting documents into chunks...")
                chunks = await asyncio.to_thread(
                    self.indexer.text_splitter.split_documents, docs
                )
                logger.info(f"Created {len(chunks)} chunks from the document")

                logger.info("Adding chunks to vector store...")
                await asyncio.to_thread(self.indexer.vector_store.add_documents, chunks)
                logger.info("Successfully added chunks to vector store")

                return {
                    "status": "success",
                    "message": "Document processed successfully",
                    "file_name": Path(file_path).name,
                    "chunks": len(chunks),
                }

            except Exception as e:
                logger.error(f"Failed to process document: {str(e)}")
                raise


async def process_document(
    content: bytes, file_name: str, content_type: str, indexer: IndexerService
) -> Dict[str, Union[str, int]]:
    """
    Process a document with support for concurrent requests.

    Args:
        content (bytes): The file content
        file_name (str): Original file name
        content_type (str): File content type
        indexer (IndexerService): The indexer service instance

    Returns:
        Dict[str, Union[str, int]]: Processing result

    Raises:
        RuntimeError: If document processing fails
    """
    logger.info(f"Processing document: {file_name}")
    document_service = DocumentService()

    if not file_name:
        raise ValueError("No file name provided.")

    extension = Path(file_name).suffix

    with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
        try:
            # Write content to temporary file
            async with aiofiles.open(temp_file.name, "wb") as temp_async_file:
                await temp_async_file.write(content)
            logger.debug(f"Temporary file created at: {temp_file.name}")

            # Process the document
            result = await document_service.process_document(temp_file.name)
            logger.info("Document processing completed successfully")
            return result

        except Exception as e:
            error_msg = f"Document processing failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        finally:
            # Clean up temporary file
            try:
                Path(temp_file.name).unlink()
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {e}")
