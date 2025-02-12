from typing import Optional

from src.services.indexer_service import IndexerService


class Dependency:
    """
    Provider class that manages the lifecycle of service instances.
    Implements the Singleton pattern to ensure only one instance exists per service.
    """

    # Class variable to store single instance
    _indexer_instance: Optional[IndexerService] = None

    @classmethod
    def get_indexer_instance(cls) -> IndexerService:
        """
        Get or create the Indexer instance.

        Returns:
            Indexer: The singleton instance of the Indexer
        """
        try:
            if cls._indexer_instance is None:
                cls._indexer_instance = IndexerService()
                if not cls._indexer_instance.is_initialized:
                    cls._indexer_instance.initialize()
            return cls._indexer_instance
        except Exception as e:
            raise Exception(f"Error initializing Indexer: {str(e)}")


def get_indexer():
    """
    Dependency provider function for FastAPI.

    Returns:
        Indexer: The singleton Indexer instance
    """
    return Dependency.get_indexer_instance()
