"""
QCTSS Admin SDK Exception Classes
"""

class QCTSSAdminError(Exception):
    """Base exception for QCTSS Admin SDK"""

    def __init__(
        self,
        message: str,
        http_status: int = None,
        error_code: str = None,
        backend_message: str = None,
        details: dict = None,
    ):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.error_code = error_code
        self.backend_message = backend_message
        self.details = details or {}

    def __str__(self) -> str:
        parts = [self.message]

        if self.http_status:
            parts.append(f"HTTP {self.http_status}")

        if self.error_code:
            parts.append(f"Code: {self.error_code}")

        if self.backend_message:
            parts.append(f"Backend: {self.backend_message}")

        return " | ".join(parts)

class PermissionError(QCTSSAdminError):
    """Raised when admin permissions are required but not available"""
    pass

class BillingClientError(QCTSSAdminError):
    """Raised when billing operations fail"""
    pass

class InvalidBillingPeriodError(BillingClientError):
    """Raised when billing period parameters are invalid"""
    pass

class TimeoutError(QCTSSAdminError):
    """Raised when request times out"""
    pass

class AuthenticationError(QCTSSAdminError):
    """Raised when authentication fails"""
    pass

class QCSetupNotActiveError(QCTSSAdminError):
    """Raised when QCSetup status is not active"""
    pass

class QCSetupNotFoundError(QCTSSAdminError):
    """Raised when QCSetup does not exist"""
    pass

class QCSetupConfigNotFoundError(QCTSSAdminError):
    """Raised when QCSetup exists but has no activated config"""
    pass


# --- Job exceptions ---

class ValidationError(QCTSSAdminError):
    """Raised when request parameters are invalid"""
    pass


class JobClientError(QCTSSAdminError):
    """Base exception for job-related errors"""
    pass


class JobNotFoundError(JobClientError):
    """Raised when the requested job does not exist"""
    pass


class InvalidJobStateError(JobClientError):
    """Raised when the job cannot perform the requested operation in its current state"""
    pass


# --- WebSocket exceptions ---

class WebSocketError(QCTSSAdminError):
    """Base exception for WebSocket errors"""
    pass


class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection fails"""
    pass


class WebSocketAuthError(WebSocketError):
    """Raised when WebSocket authentication fails"""
    pass