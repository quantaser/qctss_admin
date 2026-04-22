# QCTSS Admin SDK

A Python SDK for administrative operations on the QCTSS (Quantum Computing Test Space Scheduler) platform.

## Installation

```bash
pip install git+https://github.com/quantaser/qctss_admin.git
```

For development installation:

```bash
git clone https://github.com/quantaser/qctss_admin.git
cd qctss_admin
pip install -e ".[dev]"
```

## Quick Start

```python
from pathlib import Path
from qctss_admin import QCTSSAdmin

# Initialize admin client (requires admin token)
admin = QCTSSAdmin(admin_token="your-admin-token")

# Check existing jobs — useful to detect stale queued/running jobs from previous sessions
job_statuses = admin.get_my_jobs_status()
if job_statuses:
    print("Existing active jobs:")
    for s in job_statuses:
        print(f"  Job {s.job_id:>6}  status={s.status:<12}  service={s.service_name}  qc_setups={s.qc_setup_list}")
else:
    print("No active jobs.")

DOWNLOAD_DIR = Path("C:/Data/qctss")

# Upload QCSetup config and wiring (admin only)
admin.upload_qcsetup_config_file(
    qcsetup_name="qc1",
    data=Path("/data/configs/qc1_config.json"),
)
admin.upload_qcsetup_wiring(
    qcsetup_name="qc1",
    data=Path("/data/wirings/qc1_wiring.json"),
)

# Batch upload configs
admin.upload_qcsetup_config_files(paths={
    "qc1": Path("/data/configs/qc1_config.json"),
    "qc2": Path("/data/configs/qc2_config.json"),
})

# Batch upload wirings
admin.upload_qcsetup_wirings(paths={
    "qc1": Path("/data/wirings/qc1_wiring.json"),
    "qc2": Path("/data/wirings/qc2_wiring.json"),
})

# Download QCSetup config files (saved to specified absolute paths)
admin.download_qcsetup_config_file(paths={
    "qc1": DOWNLOAD_DIR / "qc1_config.json",
    "qc2": DOWNLOAD_DIR / "qc2_config.json",
})

# Download QCSetup wiring files
admin.download_qcsetup_wiring(paths={
    "qc1": DOWNLOAD_DIR / "qc1_wiring.json",
    "qc2": DOWNLOAD_DIR / "qc2_wiring.json",
})

# Download billing CSV (in-memory)
csv_content = admin.download_billing_csv(year=2026, month=1)
print(csv_content)

# Download billing CSV (save to file)
csv_path = admin.download_billing_csv(
    year=2026,
    month=1,
    output_file="billing_2026_01.csv",
)
print(f"Saved to: {csv_path}")

admin.close()
```

## API Reference

### QCTSSAdmin

#### Constructor

```python
QCTSSAdmin(
    admin_token: str,
    fastapi_url: Optional[str] = None,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    retry_delay: Optional[int] = None
)
```

- `admin_token`: Admin API authentication token (required, must be type='admin')
- `fastapi_url`: FastAPI server URL (overrides build-time config, e.g. `ws://host:8001`)
- `timeout`: Request timeout in seconds (default: 30)
- `max_retries`: Max retry attempts (default: 3)
- `retry_delay`: Delay between retries (default: 5)

**Raises**:
- `AuthenticationError`: If token is invalid or not admin-level

#### download_qcsetup_config_file

```python
download_qcsetup_config_file(
    paths: Dict[str, Path]
) -> None
```

Download QCSetup config files and save each to the specified absolute path.

**Parameters**:
- `paths`: `{qcsetup_name: absolute_path}` mapping

**Returns**: `None` (files are written to the paths specified in `paths`)

**Raises**:
- `ValueError`: Any path is not absolute
- `QCSetupConfigNotFoundError`: QCSetup exists but has no activated config
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token

**Example**:
```python
admin.download_qcsetup_config_file(paths={
    "qc1": Path("/data/qc1_config.json"),
    "qc2": Path("/data/qc2_config.json"),
})
```

#### download_qcsetup_wiring

```python
download_qcsetup_wiring(
    paths: Dict[str, Path]
) -> None
```

Download QCSetup wiring files and save each to the specified absolute path.

**Parameters**:
- `paths`: `{qcsetup_name: absolute_path}` mapping

**Returns**: `None` (files are written to the paths specified in `paths`)

**Raises**:
- `ValueError`: Any path is not absolute
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token

**Example**:
```python
admin.download_qcsetup_wiring(paths={
    "qc1": Path("/data/qc1_wiring.json"),
    "qc2": Path("/data/qc2_wiring.json"),
})
```

#### upload_qcsetup_config_file

```python
upload_qcsetup_config_file(
    qcsetup_name: str,
    data: Path,
) -> dict
```

Upload a QCSetup config file from an absolute path.

**Parameters**:
- `qcsetup_name`: QCSetup name (non-empty string)
- `data`: Absolute path to a JSON file

**Returns**: Backend response JSON

**Raises**:
- `ValueError`: Path is not absolute
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token

**Example**:
```python
admin.upload_qcsetup_config_file(
    qcsetup_name="qc1",
    data=Path("/data/configs/qc1_config.json"),
)
```

#### upload_qcsetup_config_files

```python
upload_qcsetup_config_files(
    paths: Dict[str, Path],
) -> Dict[str, dict]
```

Batch-upload config files for multiple QCSetups.

**Parameters**:
- `paths`: `{qcsetup_name: absolute_path}` mapping

**Returns**: `Dict[str, dict]` — key=QCSetup name, value=backend response JSON

**Raises**:
- `ValueError`: Any path is not absolute
- `QCSetupNotActiveError`, `QCSetupNotFoundError`, `AuthenticationError`

**Example**:
```python
admin.upload_qcsetup_config_files(paths={
    "qc1": Path("/data/configs/qc1_config.json"),
    "qc2": Path("/data/configs/qc2_config.json"),
})
```

#### upload_qcsetup_wiring

```python
upload_qcsetup_wiring(
    qcsetup_name: str,
    data: Path,
) -> dict
```

Upload a QCSetup wiring file from an absolute path.

**Parameters**:
- `qcsetup_name`: QCSetup name (non-empty string)
- `data`: Absolute path to a JSON file

**Returns**: Backend response JSON

**Raises**:
- `ValueError`: Path is not absolute
- `QCSetupNotActiveError`: QCSetup status is not 'active' (403)
- `QCSetupNotFoundError`: QCSetup doesn't exist (404)
- `AuthenticationError`: Invalid or non-admin token

**Example**:
```python
admin.upload_qcsetup_wiring(
    qcsetup_name="qc1",
    data=Path("/data/wirings/qc1_wiring.json"),
)
```

#### upload_qcsetup_wirings

```python
upload_qcsetup_wirings(
    paths: Dict[str, Path],
) -> Dict[str, dict]
```

Batch-upload wiring files for multiple QCSetups.

**Parameters**:
- `paths`: `{qcsetup_name: absolute_path}` mapping

**Returns**: `Dict[str, dict]` — key=QCSetup name, value=backend response JSON

**Raises**:
- `ValueError`: Any path is not absolute
- `QCSetupNotActiveError`, `QCSetupNotFoundError`, `AuthenticationError`

**Example**:
```python
admin.upload_qcsetup_wirings(paths={
    "qc1": Path("/data/wirings/qc1_wiring.json"),
    "qc2": Path("/data/wirings/qc2_wiring.json"),
})
```

#### download_billing_csv

```python
download_billing_csv(
    year: int,
    month: int,
    output_file: Optional[Union[str, Path]] = None
) -> str
```

Download billing CSV for specified period.

**Parameters**:
- `year`: Billing year (>= 2000, <= 3000)
- `month`: Billing month (1-12)
- `output_file`: Optional file path to save CSV

**Returns**:
- If `output_file` provided: file path where CSV was saved
- If no `output_file`: CSV content as string

**Raises**:
- `InvalidBillingPeriodError`: Invalid year/month
- `AuthenticationError`: Invalid or non-admin token
- `TimeoutError`: Request timed out
- `IOError`: File write error (if output_file provided)

---

## Job Management

Admin users can manage jobs with the same scope as regular users (own jobs only).
These methods mirror the `qctss-client` job API.

#### start_job

```python
start_job(qc_setup_list: List[str], service_name: str) -> JobResponse
```

**Parameters**:
- `qc_setup_list`: List of QC setup names (non-empty strings)
- `service_name`: Name of the service to use

**Returns**: `JobResponse` with `job_id` and `status`

#### get_my_jobs_status

```python
get_my_jobs_status() -> List[JobStatus]
```

**Returns**: List of `JobStatus` objects for the current admin user's jobs

#### close_job

```python
close_job(job_id: int) -> JobResponse
```

**Parameters**:
- `job_id`: Job ID to close (positive integer)

**Returns**: `JobResponse` with updated status (`completed`)

#### cancel_job

```python
cancel_job(job_id: int, reason: Optional[str] = None) -> JobResponse
```

**Parameters**:
- `job_id`: Job ID to cancel
- `reason`: Reason for cancellation (default: `"User cancelled job"`)

**Returns**: `JobResponse` with updated status (`cancelled`)

#### wait_until_running

```python
wait_until_running(
    job_id: int,
    timeout: Optional[int] = None,
    on_status: Optional[Callable[[JobStatus], None]] = None,
) -> int
```

Wait for a job to reach `running` state. Press `Ctrl+C` to cancel waiting.

**Parameters**:
- `job_id`: Job ID to monitor
- `timeout`: Max seconds to wait (None = wait forever)
- `on_status`: Optional callback for status updates while waiting

**Returns**: Port number assigned when job is running

**Example**:
```python
from qctss_admin import (
    QCTSSAdmin,
    JobNotFoundError, InvalidJobStateError,
    WebSocketError, TimeoutError,
)

admin = QCTSSAdmin(admin_token="admin-token")

try:
    job = admin.start_job(qc_setup_list=["qc_setup_A"], service_name="my_service")
    port = admin.wait_until_running(job.job_id, timeout=300)
    print(f"Job running on port: {port}")
    admin.close_job(job.job_id)
except TimeoutError:
    admin.cancel_job(job.job_id, reason="Timeout during wait")
except KeyboardInterrupt:
    admin.cancel_job(job.job_id, reason="User interrupted")
finally:
    admin.close()
```

---

## Error Handling

### Exception Types

- **`AuthenticationError`**: Authentication failed (invalid or non-admin token)
- **`QCSetupNotActiveError`**: QCSetup status is not 'active' (403)
- **`QCSetupNotFoundError`**: QCSetup doesn't exist (404)
- **`QCSetupConfigNotFoundError`**: QCSetup exists but has no activated config
- **`InvalidBillingPeriodError`**: Invalid year/month values
- **`TimeoutError`**: Request timed out
- **`ValidationError`**: Invalid request parameters
- **`JobClientError`**: General job operation error
- **`JobNotFoundError`**: Job not found (404)
- **`InvalidJobStateError`**: Job cannot perform the operation in current state (409)
- **`WebSocketError`**: WebSocket error (base class)
- **`WebSocketConnectionError`**: WebSocket connection failed
- **`WebSocketAuthError`**: WebSocket authentication failed

### Example

```python
from pathlib import Path
from qctss_admin import (
    QCTSSAdmin,
    AuthenticationError,
    QCSetupNotActiveError,
    QCSetupNotFoundError,
    QCSetupConfigNotFoundError,
    InvalidBillingPeriodError,
    TimeoutError,
)

try:
    admin = QCTSSAdmin(admin_token="admin-token")
    admin.download_qcsetup_config_file(paths={"qc1": Path("/data/qc1_config.json")})
    csv_data = admin.download_billing_csv(2026, 1)

except AuthenticationError as e:
    print(f"Access denied: {e}")
except QCSetupNotActiveError as e:
    print(f"QCSetup is not active: {e}")
except QCSetupConfigNotFoundError as e:
    print(f"QCSetup has no activated config: {e}")
except QCSetupNotFoundError as e:
    print(f"QCSetup not found: {e}")
except InvalidBillingPeriodError as e:
    print(f"Invalid period: {e}")
except TimeoutError as e:
    print(f"Timeout: {e}")
finally:
    admin.close()
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Email: tina@quantaser.com
- Issues: [GitHub Issues](https://github.com/quantaser/qctss_admin/issues)
