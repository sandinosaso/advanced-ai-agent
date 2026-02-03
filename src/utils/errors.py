"""
Custom error classes for the application
"""


class AgentError(Exception):
    """Base exception for agent errors"""
    pass


class SQLGenerationError(AgentError):
    """Error during SQL generation"""
    pass


class SQLExecutionError(AgentError):
    """Error during SQL execution"""
    pass


class DomainResolutionError(AgentError):
    """Error during domain term resolution"""
    pass


class ValidationError(AgentError):
    """Error during validation"""
    pass
