"""
QCTSS Admin SDK

A Python SDK for administrative operations on the QCTSS quantum computing platform.
"""

__version__ = "0.1.1"
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
)

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
]