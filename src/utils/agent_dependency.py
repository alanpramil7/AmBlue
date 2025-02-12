from typing import Optional

from src.services.agent_service import AgentService


class AgentDependency:
    """
    Provider class that manages the AgentService lifecycle.
    Implements the Singleton pattern to ensure only one instance exists.
    """

    _instance: Optional[AgentService] = None

    @classmethod
    def get_instance(cls) -> AgentService:
        """
        Get or create the AgentService instance.

        Returns:
            AgentService: The singleton instance of the AgentService
        """
        try:
            if cls._instance is None:
                cls._instance = AgentService()
            return cls._instance
        except Exception as e:
            raise Exception(f"Error initializing AgentService: {str(e)}")


def get_agent():
    """
    Dependency provider function for FastAPI.

    Returns:
        AgentService: The singleton AgentService instance
    """
    return AgentDependency.get_instance()
