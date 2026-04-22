"""
QCTSS Admin SDK Utility Functions
"""

import time
import requests
from typing import Union, Dict, Any
from .exceptions import BillingClientError, TimeoutError, PermissionError

def validate_billing_period(year: int, month: int) -> None:
    """Validate billing period parameters"""
    if not (2000 <= year <= 3000):
        raise ValueError("Year must be between 2000 and 3000")
    
    if not (1 <= month <= 12):
        raise ValueError("Month must be between 1 and 12")

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
            mapped_error = map_http_error(e)
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

def map_http_error(http_error) -> Exception:
    """Map HTTP errors to appropriate SDK exceptions"""
    
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