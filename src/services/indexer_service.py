import logging
from pathlib import Path
from typing import Optional

from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters.character import RecursiveCharacterTextSplitter

from src.utils.logger import get_logger

# Initialize logger for the IndexerService
logger = get_logger("IndexerService", logging.INFO)


class IndexerService:
    """
    A service class for managing document indexing and vector storage operations.

    This class handles the initialization and management of:
    - Document embedding model
    - Text splitting functionality
    - Vector storage for document embeddings

    Attributes:
        vector_store (Optional[Chroma]): Vector database for storing document embeddings
        embedding_model (Optional[OllamaEmbeddings]): Model for generating document embeddings
        text_splitter (Optional[RecursiveCharacterTextSplitter]): Utility for splitting text into chunks
    """

    def __init__(self):
        """
        Initialize the IndexerService with required components.

        Sets up:
        - Vector store (Chroma)
        - Embedding model (Ollama)
        - Text splitter
        """
        # Initialize instance variables
        self.vector_store: Optional[Chroma] = None
        self.embedding_model: Optional[OllamaEmbeddings] = None
        self.text_splitter: Optional[RecursiveCharacterTextSplitter] = None
        self._is_initialized: bool = False

        # Perform initial setup
        self.initialize()

    def initialize(self) -> None:
        """
        Initialize all required components of the indexer service.

        This method handles the setup sequence for:
        1. Embedding model
        2. Text splitter
        3. Vector store
        """
        logger.info("Initializing Indexer Service components...")
        self._setup_embedding_model()
        self._setup_text_splitter()
        self._setup_vector_store()
        self.is_initialized = True

    def _setup_embedding_model(self) -> None:
        """
        Initialize the embedding model using Ollama.

        Uses the 'nomic-embed-text' model for generating document embeddings.
        """
        logger.info("Setting up embedding model...")
        self.embedding_model = OllamaEmbeddings(model="nomic-embed-text")
        logger.info("Embedding model setup complete.")

    def _setup_text_splitter(self) -> None:
        """
        Initialize the text splitter with specific configuration.

        Configuration:
        - chunk_size: 1000 characters
        - chunk_overlap: 200 characters
        - separators: Various text separators for intelligent splitting
        """
        logger.info("Setting up text splitter...")
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            # Separators ordered by priority
            separators=["\n\n", "\n", ".", "?", "!", " ", ""],
        )
        logger.info("Text splitter setup complete.")

    def _setup_vector_store(self) -> None:
        """
        Initialize the vector store for document embeddings.

        Sets up:
        - Persistent storage directory in the project's data folder
        - Chroma DB configuration with telemetry disabled
        - Embedding function connection

        The vector store is configured to:
        - Persist data to disk
        - Disable anonymous telemetry
        - Use the specified embedding model
        """
        logger.info("Setting up vector store...")

        # Get project root and create data directory
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data" / "vector_store"
        data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Vector store directory: {data_dir}")

        # Initialize Chroma with specific settings
        self.vector_store = Chroma(
            persist_directory=str(data_dir),
            embedding_function=self.embedding_model,
            client_settings=Settings(
                anonymized_telemetry=False,  # Disable anonymous data collection
                is_persistent=True,  # Enable persistence to disk
            ),
        )
        logger.info("Vector store setup complete.")
