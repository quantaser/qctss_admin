"""
QCTSS Admin SDK Utility Functions
"""

import time
import logging
from typing import Union, Dict, Any, Optional
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .exceptions import (
    QCTSSAdminError,
    BillingClientError,
    TimeoutError,
    PermissionError,
    AuthenticationError,
    JobNotFoundError,
    InvalidJobStateError,
    ValidationError,
    JobClientError,
)

logger = logging.getLogger(__name__)

# SDK identification
try:
    from importlib.metadata import version as _pkg_version
    _SDK_VERSION = _pkg_version("qctss-admin")
except Exception:
    _SDK_VERSION = "unknown"
_SDK_NAME = "qctss-admin"

# ---------------------------------------------------------------------------
# Billing-specific helpers (legacy, kept for backward compatibility)
# ---------------------------------------------------------------------------

def format_billing_period(year: int, month: int) -> str:
    """Format billing period for API calls"""
    return f"{year}-{month:02d}"

def make_http_request(
    method: str,
    url: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: int = 5,
    **kwargs
) -> requests.Response:
    """Make HTTP request with retry logic"""
    
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            # Make the request
            response = getattr(requests, method.lower())(
                url,
                timeout=timeout,
                **kwargs
            )
            
            # Check for HTTP errors
            response.raise_for_status()
            return response
            
        except requests.Timeout as e:
            last_exception = TimeoutError(f"Request timeout after {timeout} seconds")
            
        except requests.ConnectionError as e:
            last_exception = BillingClientError(f"Connection error: {e}")
            
        except requests.HTTPError as e:
            # Map HTTP errors
            mapped_error = _map_billing_http_error(e)
            if attempt == max_retries:  # Last attempt
                raise mapped_error
            last_exception = mapped_error
            
        except Exception as e:
            last_exception = BillingClientError(f"Unexpected error: {e}")
        
        # Sleep before retry (except on last attempt)
        if attempt < max_retries:
            time.sleep(retry_delay)
    
    # If we get here, all retries failed
    raise last_exception

def _map_billing_http_error(http_error) -> Exception:
    """Map HTTP errors to appropriate SDK exceptions (billing legacy helper)"""
    
    # Handle timeout errors specifically
    if isinstance(http_error, requests.Timeout):
        return TimeoutError(f"HTTP request timeout: {http_error}")
    
    if hasattr(http_error, 'response') and http_error.response is not None:
        status_code = http_error.response.status_code
        response_text = http_error.response.text
        
        if status_code == 403:
            return PermissionError(f"Access denied (403): {response_text}")
        elif status_code == 401:
            return PermissionError(f"Authentication failed (401): {response_text}")
        elif status_code >= 500:
            return BillingClientError(f"Server error ({status_code}): {response_text}")
        else:
            return BillingClientError(f"HTTP error ({status_code}): {response_text}")
    else:
        return BillingClientError(f"HTTP error: {http_error}")


def validate_billing_period(year: int, month: int) -> None:
    """Validate billing period parameters
    
    Args:
        year: Billing year
        month: Billing month (1-12)
        
    Raises:
        ValueError: If year or month is invalid
    """
    if year < 2000:
        raise ValueError(f"Invalid year: {year}. Must be >= 2000")
    
    if not (1 <= month <= 12):
        raise ValueError(f"Invalid month: {month}. Must be between 1 and 12")


def format_billing_period(year: int, month: int) -> str:
    """Format billing period as YYYY-MM string
    
    Args:
        year: Billing year
        month: Billing month (1-12)
        
    Returns:
        Formatted period string (e.g., "2026-01")
    """
    return f"{year:04d}-{month:02d}"


# ---------------------------------------------------------------------------
# General HTTP helpers (aligned with qctss-client utils.py)
# ---------------------------------------------------------------------------

class RetryHTTPAdapter(HTTPAdapter):
    """HTTP adapter with automatic retry on 5xx errors"""

    def __init__(self, max_retries: int = 3, retry_delay: int = 5):
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[500, 502, 503, 504],
            backoff_factor=retry_delay,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"],
        )
        super().__init__(max_retries=retry_strategy)


def create_session(max_retries: int = 3, retry_delay: int = 5) -> requests.Session:
    """Create a requests session with retry configuration"""
    session = requests.Session()
    adapter = RetryHTTPAdapter(max_retries=max_retries, retry_delay=retry_delay)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def make_request(
    method: str,
    base_url: str,
    endpoint: str,
    token: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: int = 5,
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> requests.Response:
    """
    Make HTTP request with retry logic and unified X-API-KEY authentication.

    Args:
        method: HTTP method (GET, POST, etc.)
        base_url: Base URL for the API
        endpoint: API endpoint path
        token: Authentication token (sent as X-API-KEY header)
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Base delay between retries in seconds
        data: Request body data
        params: Query string parameters

    Returns:
        requests.Response

    Raises:
        QCTSSAdminError subclass on HTTP errors
        TimeoutError on timeout
    """
    url = urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))

    request_headers = {
        "X-API-KEY": token,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-SDK-Name": _SDK_NAME,
        "X-SDK-Version": _SDK_VERSION,
    }

    session = create_session(max_retries=max_retries, retry_delay=retry_delay)

    try:
        logger.debug(f"Making {method} request to {url}")
        response = session.request(
            method=method,
            url=url,
            json=data,
            params=params,
            headers=request_headers,
            timeout=timeout,
        )

        if not response.ok:
            error = map_http_error(response.status_code, response.text)
            logger.error(f"HTTP {response.status_code} error: {response.text}")
            raise error

        logger.debug(f"Request successful: {method} {url} -> {response.status_code}")
        return response

    except requests.exceptions.Timeout as e:
        logger.error(f"Request timeout: {url}")
        raise TimeoutError(
            f"Request timed out after {timeout}s",
            details={"url": url, "timeout": timeout},
        ) from e

    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {url}")
        raise QCTSSAdminError(
            f"Connection failed to {url}",
            error_code="CONNECTION_ERROR",
            details={"url": url},
        ) from e

    except requests.exceptions.RequestException as e:
        if isinstance(e, requests.exceptions.Timeout):
            raise
        logger.error(f"Request error: {url} - {str(e)}")
        raise QCTSSAdminError(
            f"Request failed: {str(e)}",
            error_code="REQUEST_ERROR",
            details={"url": url},
        ) from e

    finally:
        session.close()


def get(
    base_url: str,
    endpoint: str,
    token: str,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: int = 5,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """GET request. Returns parsed JSON response."""
    response = make_request(
        method="GET",
        base_url=base_url,
        endpoint=endpoint,
        token=token,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        params=params,
    )
    return response.json()


def post(
    base_url: str,
    endpoint: str,
    token: str,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    max_retries: int = 3,
    retry_delay: int = 5,
) -> Dict[str, Any]:
    """POST request. Returns parsed JSON response."""
    response = make_request(
        method="POST",
        base_url=base_url,
        endpoint=endpoint,
        token=token,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        data=data,
    )
    return response.json()


def map_http_error(status_code: int, response_text: str = "") -> QCTSSAdminError:
    """
    Map HTTP status codes to appropriate admin SDK exceptions.

    Args:
        status_code: HTTP status code
        response_text: Response body text

    Returns:
        Appropriate QCTSSAdminError subclass (not raised, caller raises it)
    """
    error_details = {"status_code": status_code, "response": response_text}

    if status_code == 401:
        return AuthenticationError(
            "Authentication failed",
            http_status=status_code,
            error_code="UNAUTHORIZED",
            backend_message=response_text,
            details=error_details,
        )
    elif status_code == 403:
        return PermissionError(
            "Access denied",
            http_status=status_code,
            error_code="FORBIDDEN",
            backend_message=response_text,
            details=error_details,
        )
    elif status_code == 404:
        return JobNotFoundError(
            "Resource not found",
            http_status=status_code,
            error_code="NOT_FOUND",
            backend_message=response_text,
            details=error_details,
        )
    elif status_code == 409:
        return InvalidJobStateError(
            "Invalid job state",
            http_status=status_code,
            error_code="CONFLICT",
            backend_message=response_text,
            details=error_details,
        )
    elif status_code == 422:
        return ValidationError(
            "Validation failed",
            http_status=status_code,
            error_code="VALIDATION_ERROR",
            backend_message=response_text,
            details=error_details,
        )
    elif 400 <= status_code < 500:
        return JobClientError(
            f"Client error: {status_code}",
            http_status=status_code,
            error_code="CLIENT_ERROR",
            backend_message=response_text,
            details=error_details,
        )
    elif 500 <= status_code < 600:
        return QCTSSAdminError(
            f"Server error: {status_code}",
            http_status=status_code,
            error_code="SERVER_ERROR",
            backend_message=response_text,
            details=error_details,
        )
    else:
        return QCTSSAdminError(
            f"HTTP error: {status_code}",
            http_status=status_code,
            error_code="HTTP_ERROR",
            backend_message=response_text,
            details=error_details,
        )