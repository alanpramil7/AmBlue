from typing import Optional

from src.services.database_service import DatabaseService
from src.services.indexer_service import IndexerService


class Dependency:
    """
    Provider class that manages the lifecycle of service instances.
    Implements the Singleton pattern to ensure only one instance exists per service.
    """

    # Class variable to store single instance
    _indexer_instance: Optional[IndexerService] = None
    _database_instance: Optional[DatabaseService] = None

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

    @classmethod
    def get_database_instance(cls) -> DatabaseService:
        """
        Get or create the Database instance.

        Returns:
            Database: The singleton instance of the Database
        """
        try:
            if cls._database_instance is None:
                cls._database_instance = DatabaseService()
                if not cls._database_instance.is_initialized:
                    cls._database_instance.initialize()
            return cls._database_instance
        except Exception as e:
            raise Exception(f"Error initializing Indexer: {str(e)}")


def get_indexer():
    """
    Dependency provider function for FastAPI.

    Returns:
        Indexer: The singleton Indexer instance
    """
    return Dependency.get_indexer_instance()


def get_database():
    """"""
    return Dependency.get_database_instance()
