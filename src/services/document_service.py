import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Union

from fastapi import UploadFile
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader
from langchain_core.documents.base import Document

from src.utils.dependency import get_indexer
from src.utils.logger import get_logger

# Initialize logger for the module (removed duplicate initialization)
logger = get_logger("DocumentService", logging.INFO)


class DocumentService:
    """
    Service class for handling document processing operations including loading and indexing.
    Supports multiple document formats and provides vector store indexing capabilities.
    """

    def __init__(self):
        """
        Initialize DocumentService with required dependencies and supported file formats.
        Sets up the indexer and defines supported document extensions.
        """
        logger.info("Initializing DocumentService")
        self.indexer = get_indexer()
        # Dictionary mapping file extensions to their respective loader classes
        self.supported_extensions = {"pdf": PyPDFLoader, "docx": Docx2txtLoader}
        logger.info(
            f"Supported file extensions: {', '.join(self.supported_extensions.keys())}"
        )

    def _create_document(self, file_path: str) -> List[Document]:
        """
        Create document objects from the input file.

        Args:
            file_path (str): Path to the document file

        Returns:
            List[Document]: List of created document objects

        Raises:
            ValueError: If file format is not supported
        """
        logger.info(f"Creating document objects from file: {file_path}")

        # Extract and validate file extension
        extension = Path(file_path).suffix.lower().lstrip(".")
        logger.debug(f"Detected file extension: {extension}")

        if extension not in self.supported_extensions:
            error_msg = (
                f"Unsupported file format: {extension}. "
                f"Supported formats are: {', '.join(self.supported_extensions.keys())}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Load document using appropriate loader
        loader_class = self.supported_extensions[extension]
        logger.info(f"Using loader class: {loader_class.__name__}")

        try:
            documents = loader_class(file_path).load()
            logger.info(f"Successfully created {len(documents)} document objects")
            return documents
        except Exception as e:
            logger.error(f"Failed to load document: {str(e)}")
            raise

    def index_document(self, file_path: str) -> Dict[str, Union[str, int]]:
        """
        Process and index the document into the vector store.

        Args:
            file_path (str): Path to the document file

        Returns:
            Dict[str, Union[str, int]]: Processing result containing status and metrics

        Raises:
            RuntimeError: If indexer components are not properly initialized
        """
        logger.info(f"Starting document indexing process for: {file_path}")

        # Validate indexer components
        if not self.indexer.text_splitter or not self.indexer.vector_store:
            error_msg = "Indexer components not properly initialized"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            # Document processing pipeline
            docs = self._create_document(file_path)
            logger.info("Splitting documents into chunks...")
            chunks = self.indexer.text_splitter.split_documents(docs)
            logger.info(f"Created {len(chunks)} chunks from the document")

            logger.info("Adding chunks to vector store...")
            self.indexer.vector_store.add_documents(chunks)
            logger.info("Successfully added chunks to vector store")

            result = {
                "message": "Document processed successfully",
                "file_name": Path(file_path).name,
                "chunks": len(chunks),
            }
            logger.info(f"Document processing completed: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to process document: {str(e)}")
            raise


async def process_document(file: UploadFile) -> Dict[str, Union[str, int]]:
    """
    Asynchronously process an uploaded document.

    Args:
        file (UploadFile): The uploaded file object

    Returns:
        Dict[str, Union[str, int]]: Processing result

    Raises:
        RuntimeError: If document processing fails
    """
    logger.info(f"Starting async document processing for file: {file.filename}")
    document_service = DocumentService()

    if not file.filename:
        raise ValueError("No file name provided.")

    extension = Path(file.filename).suffix

    with NamedTemporaryFile(delete=True, suffix=extension) as temp_file:
        try:
            # Handle file upload
            logger.info("Reading uploaded file content...")
            content = await file.read()

            logger.info("Writing content to temporary file...")
            temp_file.write(content)
            temp_file.flush()
            logger.debug(f"Temporary file created at: {temp_file.name}")

            # Process the document
            result = document_service.index_document(temp_file.name)
            logger.info("Document processing completed successfully")
            return result

        except Exception as e:
            error_msg = f"Document processing failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
