class ServiceError(Exception):
    """Base class for all service-related errors."""


class ServiceValidationError(ServiceError):
    """Raised when there is a validation error in the service layer."""

    def __init__(self, errors: dict[str, list[str]]):
        self.errors = errors
        super().__init__("Validation failed")


class ServiceNotFoundError(ServiceError):
    """Raised when a requested resource is not found."""


class ServicePermissionError(ServiceError):
    """Raised when a user does not have permission to perform an action."""
