class ServiceError(Exception):
    """Base class for all service-related errors."""

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message or str(self)

class ServiceValidationError(ServiceError):
    """Raised when there is a validation error in the service layer."""

    def __init__(self, errors: dict[str, list[str]]):
        self.errors = errors
        super().__init__("Validation failed")


class ServiceNotFoundError(ServiceError):
    """Raised when a requested resource is not found."""


class ServicePermissionError(ServiceError):
    """Raised when a user does not have permission to perform an action."""


class SubscriptionLimitError(ServiceError):
    """
    Raised when a subscription feature limit is reached or disabled.
    """

    def __init__(self, message: str, code: str = "limit_reached"):
        self.code = code
        super().__init__(message)
