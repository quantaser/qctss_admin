"""
QCTSS Admin Client for administrative operations
"""
import io
import csv
import json
import time
import threading
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Callable
import logging

import requests
from .config import BackendConfig
from .exceptions import (
    AuthenticationError, QCSetupNotActiveError, QCSetupNotFoundError, QCSetupConfigNotFoundError,
    ValidationError, JobClientError, JobNotFoundError, InvalidJobStateError,
    BillingClientError, InvalidBillingPeriodError, TimeoutError, PermissionError,
)
from .models import JobResponse, JobStatus
from .websocket_manager import WebSocketManager
from . import utils

logger = logging.getLogger(__name__)

# SDK identification for version checking
try:
    from importlib.metadata import version as _pkg_version
    _SDK_VERSION = _pkg_version("qctss-admin")
except Exception:
    _SDK_VERSION = "unknown"
_SDK_NAME = "qctss-admin"


class QCTSSAdmin:
    """
    QCTSS Admin client for administrative operations
    """
    
    def __init__(
        self,
        admin_token: str,
        backend_url: Optional[str] = None,
        fastapi_url: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
        retry_delay: Optional[int] = None,
    ):
        """
        Initialize QCTSS Admin client
        
        Args:
            admin_token: Admin authentication token
            backend_url: Backend API URL (overrides config)
            fastapi_url: FastAPI server URL (overrides config)
            timeout: Request timeout in seconds (overrides config)
            max_retries: Max retry attempts (overrides config)
            retry_delay: Delay between retries in seconds (overrides config)
            
        Raises:
            AuthenticationError: Token is invalid or not admin-level
        """
        self.admin_token = admin_token
        self.config = BackendConfig(
            backend_url=backend_url,
            fastapi_url=fastapi_url,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        
        # Verify admin token
        self._verify_admin_token()

        # Job WebSocket state
        self._websocket_connections: Dict[int, Any] = {}
        self._websocket_manager = WebSocketManager()

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
        paths: Dict[str, Path],
    ) -> None:
        """
        批次下載多個 QCSetup 的 config 檔案並儲存至指定絕對路徑。

        Args:
            paths: {qcsetup_name: 絕對路徑} 對映表

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupConfigNotFoundError: QCSetup 無 activated config
            QCSetupNotFoundError: QCSetup 不存在
        """
        for name, output_path in paths.items():
            if not Path(output_path).is_absolute():
                raise ValueError(f"Path for '{name}' must be absolute: {output_path}")

        for name, output_path in paths.items():
            output_path = Path(output_path)

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

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response.text, encoding='utf-8')
    
    def download_qcsetup_wiring(
        self,
        paths: Dict[str, Path],
    ) -> None:
        """
        批次下載多個 QCSetup 的 wiring 檔案並儲存至指定絕對路徑。

        Args:
            paths: {qcsetup_name: 絕對路徑} 對映表

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        for name, output_path in paths.items():
            if not Path(output_path).is_absolute():
                raise ValueError(f"Path for '{name}' must be absolute: {output_path}")

        for name, output_path in paths.items():
            output_path = Path(output_path)

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

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(response.text, encoding='utf-8')
    
    def upload_qcsetup_config_file(
        self,
        qcsetup_name: str,
        data: Path,
    ) -> dict:
        """
        上傳 QCSetup config 檔案（單一 name）。

        Args:
            qcsetup_name: QCSetup name
            data: 絕對路徑（JSON 檔案）

        Returns:
            Backend response JSON

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        if not data.is_absolute():
            raise ValueError(f"Path must be absolute: {data}")
        with open(data, 'r', encoding='utf-8') as f:
            payload = json.load(f)

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
        data: Path,
    ) -> dict:
        """
        上傳 QCSetup wiring 檔案（單一 name）。

        Args:
            qcsetup_name: QCSetup name
            data: 絕對路徑（JSON 檔案）

        Returns:
            Backend response JSON

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        if not data.is_absolute():
            raise ValueError(f"Path must be absolute: {data}")
        with open(data, 'r', encoding='utf-8') as f:
            payload = json.load(f)

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
    
    def upload_qcsetup_config_files(
        self,
        paths: Dict[str, Path],
    ) -> Dict[str, dict]:
        """
        批次上傳多個 QCSetup 的 config 檔案（從絕對路徑讀取）。

        Args:
            paths: {qcsetup_name: 絕對路徑} 對映表

        Returns:
            Dict[str, dict] - key 為 qcsetup_name，value 為 backend response JSON

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        for name, input_path in paths.items():
            if not Path(input_path).is_absolute():
                raise ValueError(f"Path for '{name}' must be absolute: {input_path}")
        return {name: self.upload_qcsetup_config_file(qcsetup_name=name, data=Path(p)) for name, p in paths.items()}

    def upload_qcsetup_wirings(
        self,
        paths: Dict[str, Path],
    ) -> Dict[str, dict]:
        """
        批次上傳多個 QCSetup 的 wiring 檔案（從絕對路徑讀取）。

        Args:
            paths: {qcsetup_name: 絕對路徑} 對映表

        Returns:
            Dict[str, dict] - key 為 qcsetup_name，value 為 backend response JSON

        Raises:
            ValueError: 路徑非絕對路徑
            QCSetupNotActiveError: QCSetup 狀態非 active
            QCSetupNotFoundError: QCSetup 不存在
        """
        for name, input_path in paths.items():
            if not Path(input_path).is_absolute():
                raise ValueError(f"Path for '{name}' must be absolute: {input_path}")
        return {name: self.upload_qcsetup_wiring(qcsetup_name=name, data=Path(p)) for name, p in paths.items()}

    # ------------------------------------------------------------------
    # Internal HTTP helpers for job endpoints
    # ------------------------------------------------------------------

    def _call_fastapi_job_query(self) -> List[Dict[str, Any]]:
        """GET job status list from FastAPI server via utils (X-API-KEY auth)"""
        http_url = (
            self.config.fastapi_url
            .replace("ws://", "http://")
            .replace("wss://", "https://")
            .rstrip("/")
        )
        return utils.get(
            base_url=http_url,
            endpoint="/fastapi/job/status",
            token=self.admin_token,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )

    # ------------------------------------------------------------------
    # Job methods (same scope as qctss-client)
    # ------------------------------------------------------------------

    def start_job(self, qc_setup_list: List[str], service_name: str) -> JobResponse:
        """
        Start a new event job.

        Args:
            qc_setup_list: List of QC setup names
            service_name: Name of the service to use

        Returns:
            JobResponse with job_id and status

        Raises:
            ValidationError: Invalid parameters
            JobClientError: Job creation failed
            TimeoutError: Request timed out
        """
        if not qc_setup_list or not all(qc_setup_list):
            raise ValidationError("qc_setup_list cannot be empty and must not contain empty strings")
        if not service_name or not service_name.strip():
            raise ValidationError("service_name cannot be empty")

        data = {
            "qc_setup_list": qc_setup_list,
            "service_name": service_name.strip(),
        }
        response_data = utils.post(
            base_url=self.config.backend_url,
            endpoint="/api/jobs/",
            token=self.admin_token,
            data=data,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )
        return JobResponse(**response_data)

    def get_my_jobs_status(self) -> List[JobStatus]:
        """
        Get status of all jobs for the current admin user via FastAPI server.

        Returns:
            List of JobStatus objects

        Raises:
            JobClientError: Request failed
            TimeoutError: Request timed out
        """
        response_data = self._call_fastapi_job_query()
        return [JobStatus(**item) for item in response_data]

    def close_job(self, job_id: int) -> JobResponse:
        """
        Close a job (mark as completed).

        Args:
            job_id: Job ID to close

        Returns:
            JobResponse with updated status

        Raises:
            ValidationError: Invalid job_id
            JobNotFoundError: Job not found
            InvalidJobStateError: Job cannot be closed in current state
            TimeoutError: Request timed out
        """
        if not isinstance(job_id, int) or job_id <= 0:
            raise ValidationError(f"Invalid job_id: {job_id}. Must be positive integer.")

        response_data = utils.post(
            base_url=self.config.backend_url,
            endpoint=f"/api/jobs/{job_id}/close/",
            token=self.admin_token,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )
        result = JobResponse(**response_data)

        if job_id in self._websocket_connections:
            self.unsubscribe_job_updates(job_id)

        return result

    def cancel_job(self, job_id: int, reason: Optional[str] = None) -> JobResponse:
        """
        Cancel a job.

        Args:
            job_id: Job ID to cancel
            reason: Optional reason for cancellation

        Returns:
            JobResponse with updated status

        Raises:
            ValidationError: Invalid job_id
            JobNotFoundError: Job not found
            InvalidJobStateError: Job cannot be cancelled in current state
            TimeoutError: Request timed out
        """
        if not isinstance(job_id, int) or job_id <= 0:
            raise ValidationError(f"Invalid job_id: {job_id}. Must be positive integer.")

        data = {"reason": reason or "User cancelled job"}
        response_data = utils.post(
            base_url=self.config.backend_url,
            endpoint=f"/api/jobs/{job_id}/cancel/",
            token=self.admin_token,
            data=data,
            timeout=self.config.timeout,
            max_retries=self.config.max_retries,
            retry_delay=self.config.retry_delay,
        )
        result = JobResponse(**response_data)

        if job_id in self._websocket_connections:
            self.unsubscribe_job_updates(job_id)

        return result

    def subscribe_job_updates(
        self,
        job_id: int,
        callback: Optional[Callable[[JobStatus], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """
        Subscribe to real-time job status updates via WebSocket.

        Args:
            job_id: Job ID to monitor
            callback: Optional function called with JobStatus updates
            on_error: Optional error handler function

        Raises:
            ValidationError: Invalid job_id
            WebSocketError: Connection failed
        """
        if not isinstance(job_id, int) or job_id <= 0:
            raise ValidationError(f"Invalid job_id: {job_id}. Must be positive integer.")

        if callback is None:
            callback = lambda status: None

        self._websocket_manager.connect(
            job_id=job_id,
            websocket_url=self.config.websocket_url,
            token=self.admin_token,
            callback=callback,
            on_error=on_error,
        )
        self._websocket_connections[job_id] = True
        logger.info(f"Subscribed to job {job_id} updates")

    def unsubscribe_job_updates(self, job_id: int) -> None:
        """
        Unsubscribe from job status updates.

        Args:
            job_id: Job ID to stop monitoring
        """
        if job_id in self._websocket_connections:
            self._websocket_manager.disconnect(job_id)
            del self._websocket_connections[job_id]
            logger.info(f"Unsubscribed from job {job_id} updates")

    def wait_until_running(
        self,
        job_id: int,
        timeout: Optional[int] = None,
        on_status: Optional[Callable[[JobStatus], None]] = None,
    ) -> int:
        """
        Wait for a job to transition from queued to running state.

        Automatically subscribes to WebSocket, monitors status, and returns
        the port number when job reaches 'running'. Disconnects WebSocket
        when done.

        Args:
            job_id: Job ID to monitor
            timeout: Maximum seconds to wait (None = wait forever)
            on_status: Optional callback for status updates while waiting

        Returns:
            port_number: Port number assigned when job is running

        Raises:
            ValidationError: Invalid job_id
            TimeoutError: Job did not reach 'running' within timeout
            WebSocketError: Connection failed
            KeyboardInterrupt: User pressed Ctrl+C
        """
        if not isinstance(job_id, int) or job_id <= 0:
            raise ValidationError(f"Invalid job_id: {job_id}. Must be positive integer.")

        job_running_event = threading.Event()
        final_port = [None]
        exception_holder = [None]

        def on_status_update(status: JobStatus):
            print(f"\n[Job {job_id}] Status: {status.status}")
            if status.queue_position is not None:
                print(f"  Queue Position: {status.queue_position}")
            if on_status:
                on_status(status)
            logger.debug(f"Job {job_id} status: {status.status}")
            time.sleep(0.2)
            if status.status == "running":
                print(f"[Job {job_id}] NOW RUNNING!")
                final_port[0] = status.port_number
                job_running_event.set()

                def defer_disconnect():
                    time.sleep(0.2)
                    try:
                        if job_id in self._websocket_connections:
                            self.unsubscribe_job_updates(job_id)
                    except Exception as e:
                        print(f"Error during deferred disconnect for job {job_id}: {e}")

                threading.Thread(target=defer_disconnect, daemon=True).start()

        def on_error(error: Exception):
            logger.error(f"WebSocket error for job {job_id}: {error}")
            exception_holder[0] = error
            job_running_event.set()

        try:
            self.subscribe_job_updates(
                job_id=job_id,
                callback=on_status_update,
                on_error=on_error,
            )

            if not job_running_event.wait(timeout=timeout):
                self.unsubscribe_job_updates(job_id)
                raise TimeoutError(
                    f"Job {job_id} did not reach 'running' state within {timeout} seconds"
                )

            if exception_holder[0]:
                raise exception_holder[0]

            if final_port[0] is not None:
                return final_port[0]
            else:
                raise RuntimeError(f"Job {job_id} reached running state but port_number is unknown")

        except KeyboardInterrupt:
            print(f"\n\nWaiting cancelled by user (Ctrl+C)")
            if job_id in self._websocket_connections:
                self.unsubscribe_job_updates(job_id)
            logger.info(f"User cancelled waiting for job {job_id} (Ctrl+C)")
            raise
        except Exception:
            if job_id in self._websocket_connections:
                self.unsubscribe_job_updates(job_id)
            raise

    def close(self) -> None:
        """Close all WebSocket connections and clean up resources"""
        self._websocket_manager.disconnect_all()
        self._websocket_connections.clear()
        logger.info("RCCI Admin client closed")