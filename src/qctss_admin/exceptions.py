"""
QCTSS Admin SDK Exception Classes
"""

class QCTSSAdminError(Exception):
    """Base exception for QCTSS Admin SDK"""
    
    def __init__(self, message: str, http_status: int = None, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.http_status = http_status
        self.error_code = error_code

class PermissionError(QCTSSAdminError):
    """Raised when admin permissions are required but not available"""
    pass

class BillingClientError(QCTSSAdminError):
    """Raised when billing operations fail"""
    pass

class InvalidBillingPeriodError(QCTSSAdminError):
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