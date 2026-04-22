"""
QCTSS Admin Client for administrative operations
"""
import io
import csv
import json
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
import logging

import requests
from .config import BackendConfig
from .exceptions import AuthenticationError, QCSetupNotActiveError, QCSetupNotFoundError, QCSetupConfigNotFoundError

logger = logging.getLogger(__name__)

# SDK identification for version checking
try:
    from importlib.metadata import version as _pkg_version
    _SDK_VERSION = _pkg_version("qctss-admin")
except Exception:
    _SDK_VERSION = "unknown"
_SDK_NAME = "qctss-admin"


class PermissionError(Exception):
    """Permission/Authorization error for admin operations"""
    pass


class BillingClientError(Exception):
    """Billing-related errors"""
    pass


class InvalidBillingPeriodError(BillingClientError):
    """Invalid billing period specified"""
    pass


class TimeoutError(Exception):
    """Request timeout error"""
    pass


class QCTSSAdmin:
    """
    QCTSS Admin client for administrative operations
    """
    
    def __init__(
        self,
        admin_token: str,
        backend_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[int] = None,
    ):
        """
        Initialize QCTSS Admin client
        
        Args:
            admin_token: Admin authentication token
            backend_url: Backend API URL (overrides config)
            timeout: Request timeout in seconds (overrides config)
            max_retries: Max retry attempts (overrides config)
            retry_delay: Delay between retries in seconds (overrides config)
            
        Raises:
            AuthenticationError: Token is invalid or not admin-level
        """
        self.admin_token = admin_token
        self.config = BackendConfig(
            backend_url=backend_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        # Verify admin token
        self._verify_admin_token()
        
        logger.info(f"Initialized QCTSS Admin client for {self.config.backend_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Return standard headers for API requests"""
        return {
            "X-API-KEY": self.admin_token,
            "Content-Type": "application/json",
            "X-SDK-Name": _SDK_NAME,
            "X-SDK-Version": _SDK_VERSION,
        }
    
    def _verify_admin_token(self) -> None:
        """
        Verify that token has admin privileges
        
        Raises:
            AuthenticationError: If token is invalid or not admin
        """
        url = self.config.get_api_url("/api/auth/verify-admin/")
        headers = {"X-API-KEY": self.admin_token}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.config.timeout)
        except requests.RequestException as e:
            raise AuthenticationError(f"Failed to connect to backend: {e}")
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid admin token")
        elif response.status_code == 403:
            raise AuthenticationError("Token is not admin type")
        elif response.status_code != 200:
            raise AuthenticationError(f"Unexpected response: {response.status_code} {response.text}")
        
        logger.debug("Admin token verification successful")
    
    def download_billing_csv(
        self, 
        year: int, 
        month: int, 
        output_file: Optional[Union[str, Path]] = None
    ) -> Union[str, str]:
        """
        Download billing CSV for specified period
        
        Args:
            year: Billing year (>= 2000)
            month: Billing month (1-12) 
            output_file: Optional file path to save CSV
            
        Returns:
            If output_file provided: file path where CSV was saved
            If no output_file: CSV content as string
            
        Raises:
            InvalidBillingPeriodError: Invalid year/month
            BillingClientError: CSV download failed
            TimeoutError: Request timed out
            PermissionError: Not authorized
        """
        # Validate parameters
        if year < 2000 or year > 3000:
            raise InvalidBillingPeriodError(f"Invalid year: {year}. Must be >= 2000 and <= 3000")
        
        if month < 1 or month > 12:
            raise InvalidBillingPeriodError(f"Invalid month: {month}. Must be 1-12")
        
        # Prepare request
        params = {"year": year, "month": month}
        headers = self._get_headers()
        
        try:
            logger.info(f"Downloading billing CSV for {year}-{month:02d}")
            
            response = requests.get(
                self.config.get_api_url("/api/export/billing-csv/"),
                params=params,
                headers=headers,
                timeout=self.config.timeout,
            )
            
            # Handle HTTP errors
            if response.status_code == 401:
                raise PermissionError("Authentication failed")
            elif response.status_code == 403:
                raise PermissionError("Not authorized to download billing data")
            elif response.status_code == 404:
                raise BillingClientError(f"No billing data found for {year}-{month:02d}")
            elif response.status_code == 422:
                raise InvalidBillingPeriodError(f"Invalid billing period: {year}-{month:02d}")
            elif not response.ok:
                raise BillingClientError(f"Download failed: HTTP {response.status_code}")
            
            # Get CSV content
            csv_content = response.text
            
            # Validate CSV content
            if not csv_content.strip():
                raise BillingClientError("Empty CSV response")
            
            # Save to file if requested
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8', newline='') as f:
                    f.write(csv_content)
                
                logger.info(f"Billing CSV saved to: {output_path}")
                return str(output_path)
            
            else:
                logger.info(f"Billing CSV downloaded ({len(csv_content)} chars)")
                return csv_content
        
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out after {self.config.timeout}s") from e
        
        except requests.exceptions.RequestException as e:
            raise BillingClientError(f"Download failed: {str(e)}") from e
    
    def download_qcsetup_config_file(
        self,
        qcsetup_names: List[str],
    ) -> Dict[str, dict]:
        """
        批次下載多個 QCSetup 的 config 檔案（in-memory）。

        Args:
            qcsetup_names: QCSetup name list

        Returns:
            Dict[str, dict] - key 為 qcsetup_name，value 為該 config 的 dict

        Raises:
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        results = {}

        for name in qcsetup_names:
            url = self.config.get_api_url(f"/api/qc-setups/by-name/{name}/download-config/")
            headers = self._get_headers()

            try:
                response = requests.get(url, headers=headers, timeout=self.config.timeout)
            except requests.RequestException as e:
                raise Exception(f"Failed to connect to backend: {e}")

            if response.status_code == 403:
                raise QCSetupNotActiveError(f"QCSetup '{name}' is not active")
            elif response.status_code == 404:
                try:
                    error_body = response.json()
                except Exception:
                    error_body = {}
                if error_body.get("error") == "No activated config found":
                    raise QCSetupConfigNotFoundError(f"QCSetup '{name}' has no activated config")
                raise QCSetupNotFoundError(f"QCSetup '{name}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to download config for '{name}': {response.status_code} {response.text}")

            # 解析 JSON 並存入 dict
            try:
                results[name] = response.json()
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response for '{name}': {e}")

        return results
    
    def download_qcsetup_wiring(
        self,
        qcsetup_names: List[str],
    ) -> Dict[str, dict]:
        """
        批次下載多個 QCSetup 的 wiring 檔案（in-memory）。

        Args:
            qcsetup_names: QCSetup name list

        Returns:
            Dict[str, dict] - key 為 qcsetup_name，value 為該 wiring 的 dict

        Raises:
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        results = {}

        for name in qcsetup_names:
            url = self.config.get_api_url(f"/api/qc-setups/by-name/{name}/download-wiring/")
            headers = self._get_headers()

            try:
                response = requests.get(url, headers=headers, timeout=self.config.timeout)
            except requests.RequestException as e:
                raise Exception(f"Failed to connect to backend: {e}")

            if response.status_code == 403:
                raise QCSetupNotActiveError(f"QCSetup '{name}' is not active")
            elif response.status_code == 404:
                raise QCSetupNotFoundError(f"QCSetup '{name}' not found")
            elif response.status_code != 200:
                raise Exception(f"Failed to download wiring for '{name}': {response.status_code} {response.text}")

            # 解析 JSON 並存入 dict
            try:
                results[name] = response.json()
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response for '{name}': {e}")

        return results
    
    def upload_qcsetup_config_file(
        self,
        qcsetup_name: str,
        data: Union[dict, str, Path],
    ) -> dict:
        """
        上傳 QCSetup config 檔案（單一 name）。

        Args:
            qcsetup_name: QCSetup name
            data: dict / JSON string / file Path

        Returns:
            Backend response JSON

        Raises:
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        # 處理 data 格式
        if isinstance(data, Path):
            with open(data, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        elif isinstance(data, str):
            payload = json.loads(data)
        elif isinstance(data, dict):
            payload = data
        else:
            raise ValueError(f"Invalid data type: {type(data)}")

        url = self.config.get_api_url(f"/api/qc-setups/by-name/{qcsetup_name}/upload-config/")
        headers = self._get_headers()

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        except requests.RequestException as e:
            raise Exception(f"Failed to connect to backend: {e}")

        if response.status_code == 403:
            raise QCSetupNotActiveError(f"QCSetup '{qcsetup_name}' is not active")
        elif response.status_code == 404:
            raise QCSetupNotFoundError(f"QCSetup '{qcsetup_name}' not found")
        elif response.status_code != 200:
            raise Exception(f"Failed to upload config for '{qcsetup_name}': {response.status_code} {response.text}")

        return response.json()
    
    def upload_qcsetup_wiring(
        self,
        qcsetup_name: str,
        data: Union[dict, str, Path],
    ) -> dict:
        """
        上傳 QCSetup wiring 檔案（單一 name）。

        Args:
            qcsetup_name: QCSetup name
            data: dict / JSON string / file Path

        Returns:
            Backend response JSON

        Raises:
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        # 處理 data 格式
        if isinstance(data, Path):
            with open(data, 'r', encoding='utf-8') as f:
                payload = json.load(f)
        elif isinstance(data, str):
            payload = json.loads(data)
        elif isinstance(data, dict):
            payload = data
        else:
            raise ValueError(f"Invalid data type: {type(data)}")

        url = self.config.get_api_url(f"/api/qc-setups/by-name/{qcsetup_name}/upload-wiring/")
        headers = self._get_headers()

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout)
        except requests.RequestException as e:
            raise Exception(f"Failed to connect to backend: {e}")

        if response.status_code == 403:
            raise QCSetupNotActiveError(f"QCSetup '{qcsetup_name}' is not active")
        elif response.status_code == 404:
            raise QCSetupNotFoundError(f"QCSetup '{qcsetup_name}' not found")
        elif response.status_code != 200:
            raise Exception(f"Failed to upload wiring for '{qcsetup_name}': {response.status_code} {response.text}")

        return response.json()
    
    def close(self) -> None:
        """Clean up resources"""
        logger.info("RCCI Admin client closed")