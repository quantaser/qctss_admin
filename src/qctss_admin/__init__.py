"""
QCTSS Admin SDK

A Python SDK for administrative operations on the QCTSS quantum computing platform.
"""

__version__ = "0.2.0"
SDK_NAME = "qctss-admin"
__author__ = "Quantaser Photonics Co. Ltd."
__email__ = "tina@quantaser.com"

from .client import (
    QCTSSAdmin,
    PermissionError,
    BillingClientError, 
    InvalidBillingPeriodError,
    TimeoutError,
)
from .exceptions import (
    AuthenticationError,
    QCSetupNotActiveError,
    QCSetupNotFoundError,
    QCSetupConfigNotFoundError,
    ValidationError,
    JobClientError,
    JobNotFoundError,
    InvalidJobStateError,
    WebSocketError,
    WebSocketConnectionError,
    WebSocketAuthError,
)
from .models import JobResponse, JobStatus

__all__ = [
    "QCTSSAdmin",
    "SDK_NAME",
    "PermissionError",
    "BillingClientError",
    "InvalidBillingPeriodError",
    "TimeoutError",
    "AuthenticationError",
    "QCSetupNotActiveError",
    "QCSetupNotFoundError",
    "QCSetupConfigNotFoundError",
    # Job exceptions
    "ValidationError",
    "JobClientError",
    "JobNotFoundError",
    "InvalidJobStateError",
    "WebSocketError",
    "WebSocketConnectionError",
    "WebSocketAuthError",
    # Job models
    "JobResponse",
    "JobStatus",
]