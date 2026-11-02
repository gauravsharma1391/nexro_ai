class AppError(Exception):
    """Raised by services; the API layer turns it into a consistent JSON error."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
