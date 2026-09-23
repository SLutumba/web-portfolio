class DuplicateUserError(Exception):
    """Raised when attempting to register an email that already exists."""

class InvalidCredentialsError(Exception):
    """Raised when attempting to login with invalid credentials (incorrect email and/or password)"""

class InvalidStatusError(Exception):
    """Raised when disallowed values for a task status is entered"""

class InvalidPriorityError(Exception):
    """Raised when disallowed values for a task priority is entered"""

class InvalidDateTimeError(Exception):
    """Raised when invalid date/datetime is entered (date in the past, perhaps)"""

class TaskNotFoundError(Exception):
    """Raised when the requested application resource was not found or is not accessible to this user"""

class InvalidPasswordError(Exception):
    """Raised when a password over 72 bytes is entered."""