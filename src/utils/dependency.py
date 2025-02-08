from typing import Optional

from src.services.indexer_service import IndexerService


class Dependency:
    """
    Provider class that manages the lifecycle of the Indexer instance.
    Implements the Singleton pattern to ensure only one Indexer instance exists.
    """

    # Class variable to store the single instance of Indexer
    _instance: Optional[IndexerService] = None

    @classmethod
    def get_indexer_instance(cls) -> IndexerService:
        """
        Get or create the Indexer instance.
        This is a class method (note the @classmethod decorator) which means it operates
        on the class itself rather than an instance.

        Returns:
            Indexer: The singleton instance of the Indexer
        """
        try:
            if cls._instance is None:
                cls._instance = IndexerService()
                if not cls._instance.is_initialized:
                    cls._instance.initialize()
            return cls._instance
        except Exception as e:
            raise Exception(f"Error initializing Indexer: {str(e)}")


def get_indexer():
    """
    Dependency provider function for FastAPI.
    This function is used with FastAPI's dependency injection system.

    Returns:
        Indexer: The singleton Indexer instance
    """
    return Dependency.get_indexer_instance()
